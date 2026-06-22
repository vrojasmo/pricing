"""
Bover Price Compliance – Web Application
"""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request, BackgroundTasks, Form, UploadFile, File
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# ── paths ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent
REPORTS_DIR = ROOT / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

sys.path.insert(0, str(ROOT))

app = FastAPI(title="Bover Price Monitor")
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))
app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

# ── in-memory job registry ─────────────────────────────────────────────────
jobs: dict[str, dict] = {}   # job_id -> {status, log, result_file}


# ── helpers ────────────────────────────────────────────────────────────────

def latest_report(ext: str) -> Optional[Path]:
    files = sorted(REPORTS_DIR.glob(f"*.{ext}"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def load_latest_json() -> list[dict]:
    p = latest_report("json")
    if not p:
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def summary_from_data(data: list[dict]) -> dict:
    retailers: dict[str, dict] = {}
    for p in data:
        r = retailers.setdefault(p["retailer"], {
            "retailer": p["retailer"],
            "country": p["country"],
            "total": 0, "ok": 0, "fail": 0, "unknown": 0,
            "max_disc": 0.0,
        })
        r["total"] += 1
        c = p.get("compliant")
        disc = p.get("discount_pct") or 0
        if c is True:
            r["ok"] += 1
        elif c is False:
            r["fail"] += 1
            r["max_disc"] = max(r["max_disc"], disc)
        else:
            r["unknown"] += 1

    total    = len(data)
    ok       = sum(1 for p in data if p.get("compliant") is True)
    fail     = sum(1 for p in data if p.get("compliant") is False)
    unknown  = total - ok - fail
    rate     = round(ok / (ok + fail) * 100, 1) if (ok + fail) else None

    return {
        "total": total, "ok": ok, "fail": fail, "unknown": unknown,
        "compliance_rate": rate,
        "retailers": sorted(retailers.values(), key=lambda r: -r["fail"]),
    }


# ── pages ──────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    data = load_latest_json()
    summary = summary_from_data(data) if data else None
    report_path = latest_report("json")
    scraped_at = None
    if report_path:
        ts_str = report_path.stem.replace("bover_prices_", "")
        try:
            scraped_at = datetime.strptime(ts_str, "%Y%m%d_%H%M%S").strftime("%d %b %Y, %H:%M UTC")
        except ValueError:
            scraped_at = report_path.name

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "summary": summary,
        "scraped_at": scraped_at,
    })


@app.get("/violations", response_class=HTMLResponse)
async def violations_page(
    request: Request,
    country: str = "",
    retailer: str = "",
    q: str = "",
):
    data = load_latest_json()
    viols = [p for p in data if p.get("compliant") is False]

    if country:
        viols = [p for p in viols if p["country"] == country]
    if retailer:
        viols = [p for p in viols if p["retailer"] == retailer]
    if q:
        ql = q.lower()
        viols = [p for p in viols if ql in p["product_name"].lower()]

    viols = sorted(viols, key=lambda p: p.get("discount_pct") or 0, reverse=True)

    retailers_list = sorted({p["retailer"] for p in data})
    return templates.TemplateResponse("violations.html", {
        "request": request,
        "violations": viols,
        "retailers": retailers_list,
        "filter_country": country,
        "filter_retailer": retailer,
        "filter_q": q,
        "total_count": len(viols),
    })


@app.get("/products", response_class=HTMLResponse)
async def products_page(
    request: Request,
    country: str = "",
    retailer: str = "",
    compliant: str = "",
    q: str = "",
    page: int = 1,
):
    data = load_latest_json()
    filtered = data

    if country:
        filtered = [p for p in filtered if p["country"] == country]
    if retailer:
        filtered = [p for p in filtered if p["retailer"] == retailer]
    if compliant == "yes":
        filtered = [p for p in filtered if p.get("compliant") is True]
    elif compliant == "no":
        filtered = [p for p in filtered if p.get("compliant") is False]
    elif compliant == "unknown":
        filtered = [p for p in filtered if p.get("compliant") is None]
    if q:
        ql = q.lower()
        filtered = [p for p in filtered if ql in p["product_name"].lower()]

    filtered = sorted(filtered, key=lambda p: (p.get("compliant") is False, p.get("discount_pct") or 0), reverse=True)

    per_page = 50
    total = len(filtered)
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(1, min(page, total_pages))
    paged = filtered[(page - 1) * per_page: page * per_page]

    retailers_list = sorted({p["retailer"] for p in data})
    return templates.TemplateResponse("products.html", {
        "request": request,
        "products": paged,
        "retailers": retailers_list,
        "filter_country": country,
        "filter_retailer": retailer,
        "filter_compliant": compliant,
        "filter_q": q,
        "page": page,
        "total_pages": total_pages,
        "total": total,
    })


@app.get("/run", response_class=HTMLResponse)
async def run_page(request: Request):
    return templates.TemplateResponse("run.html", {"request": request, "jobs": list(jobs.values())[-5:]})


@app.get("/prices", response_class=HTMLResponse)
async def prices_page(request: Request, q: str = ""):
    from bover_scraper.official_prices import OFFICIAL_PRICES, MAX_DISCOUNT_PCT
    items = sorted(OFFICIAL_PRICES.items())
    if q:
        items = [(k, v) for k, v in items if q.lower() in k]
    return templates.TemplateResponse("prices.html", {
        "request": request,
        "prices": items,
        "total": len(OFFICIAL_PRICES),
        "max_discount": MAX_DISCOUNT_PCT,
        "filter_q": q,
    })


# ── scraping job API ────────────────────────────────────────────────────────

@app.post("/api/run")
async def api_run(
    background_tasks: BackgroundTasks,
    country: str = Form(""),
    retailers: str = Form(""),   # comma-separated
):
    job_id = str(uuid.uuid4())[:8]
    jobs[job_id] = {"id": job_id, "status": "running", "log": [], "started": datetime.utcnow().isoformat(), "result": None}
    background_tasks.add_task(_run_job, job_id, country or None, [r.strip() for r in retailers.split(",") if r.strip()])
    return JSONResponse({"job_id": job_id})


async def _run_job(job_id: str, country: Optional[str], retailers: list[str]):
    cmd = [sys.executable, str(ROOT / "main.py")]
    if country:
        cmd += ["--country", country]
    if retailers:
        cmd += ["--retailers"] + retailers

    jobs[job_id]["cmd"] = " ".join(cmd)
    jobs[job_id]["log"].append(f"$ {' '.join(cmd)}\n")

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(ROOT),
    )

    async for line in proc.stdout:
        text = line.decode(errors="replace")
        jobs[job_id]["log"].append(text)

    await proc.wait()
    jobs[job_id]["status"] = "done" if proc.returncode == 0 else "error"
    jobs[job_id]["ended"] = datetime.utcnow().isoformat()

    p = latest_report("json")
    if p:
        jobs[job_id]["result"] = p.name


@app.get("/api/job/{job_id}")
async def api_job_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        return JSONResponse({"error": "not found"}, status_code=404)
    return JSONResponse(job)


@app.get("/api/job/{job_id}/stream")
async def api_job_stream(job_id: str):
    """Server-Sent Events stream for live log tailing."""
    async def generator():
        sent = 0
        while True:
            job = jobs.get(job_id)
            if not job:
                break
            log = job["log"]
            while sent < len(log):
                line = log[sent].rstrip("\n")
                yield f"data: {json.dumps(line)}\n\n"
                sent += 1
            if job["status"] in ("done", "error"):
                yield f"data: {json.dumps('__DONE__')}\n\n"
                break
            await asyncio.sleep(0.4)

    return StreamingResponse(generator(), media_type="text/event-stream")


# ── download ────────────────────────────────────────────────────────────────

@app.get("/download/{filename}")
async def download(filename: str):
    path = REPORTS_DIR / filename
    if not path.exists() or not path.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if filename.endswith(".xlsx") else "text/csv"
    return FileResponse(path, media_type=media, filename=filename)


@app.get("/api/reports")
async def api_reports():
    files = sorted(REPORTS_DIR.glob("bover_prices_*"), key=lambda p: p.stat().st_mtime, reverse=True)
    result = []
    for f in files[:20]:
        result.append({
            "name": f.name,
            "ext": f.suffix.lstrip("."),
            "size_kb": round(f.stat().st_size / 1024, 1),
            "mtime": datetime.fromtimestamp(f.stat().st_mtime).strftime("%d %b %Y %H:%M"),
        })
    return JSONResponse(result)


@app.post("/api/import-prices")
async def api_import_prices(file: UploadFile = File(...)):
    import csv, io, importlib
    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    from bover_scraper import official_prices as op
    count = 0
    for row in reader:
        name = row.get("product_name", "").strip().lower()
        try:
            price = float(row["price"])
        except (KeyError, ValueError):
            continue
        if name and price > 0:
            op.OFFICIAL_PRICES[name] = price
            count += 1
    return JSONResponse({"message": f"Se importaron {count} precios correctamente.", "total": len(op.OFFICIAL_PRICES)})


@app.get("/api/summary")
async def api_summary():
    data = load_latest_json()
    return JSONResponse(summary_from_data(data) if data else {})
