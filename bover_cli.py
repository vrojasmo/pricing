#!/usr/bin/env python3
"""
Bover Price Compliance — Interactive CLI
=========================================
Menú interactivo para consultar y ejecutar el scraper sin recordar argumentos.

Uso:
    python bover_cli.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich import box
from rich.text import Text
from rich.rule import Rule

console = Console()

SCRAPERS_META = {
    "LightingSpain":          {"country": "ES", "url": "https://lightingspain.com"},
    "MyLightShop":            {"country": "ES", "url": "https://www.mylightshop.com"},
    "LaTiendaDeIluminacion":  {"country": "ES", "url": "https://www.latiendadeiluminacion.com"},
    "Lampara.es":             {"country": "ES", "url": "https://www.lampara.es"},
    "Light11":                {"country": "DE", "url": "https://www.light11.eu"},
    "GetLight":               {"country": "DE", "url": "https://www.getlight.de"},
    "Prediger":               {"country": "DE", "url": "https://prediger.de"},
    "Reuter":                 {"country": "DE", "url": "https://www.reuter.com"},
}


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def header():
    console.print(Panel.fit(
        "[bold white]BOVER[/] [dim]·[/] [cyan]Price Compliance Monitor[/]\n"
        "[dim]España 🇪🇸  &  Alemania 🇩🇪   |   Máx. descuento permitido: 15%[/]",
        border_style="cyan",
        padding=(0, 4),
    ))
    console.print()


def find_latest_report(ext: str) -> Path | None:
    reports = sorted(Path("reports").glob(f"*.{ext}"), key=lambda p: p.stat().st_mtime, reverse=True)
    return reports[0] if reports else None


# ── Menú principal ────────────────────────────────────────────────────────────

def menu_main() -> str:
    options = {
        "1": "🚀  Ejecutar scraping completo (ES + DE)",
        "2": "🇪🇸  Ejecutar solo España",
        "3": "🇩🇪  Ejecutar solo Alemania",
        "4": "🔍  Seleccionar retailers manualmente",
        "5": "📊  Ver último informe en consola",
        "6": "📁  Abrir carpeta de informes",
        "7": "⚙️   Configurar precios oficiales",
        "8": "ℹ️   Estado de retailers",
        "0": "❌  Salir",
    }
    table = Table(box=box.ROUNDED, border_style="cyan", show_header=False, padding=(0, 2))
    table.add_column("Opción", style="bold cyan", width=6)
    table.add_column("Acción")
    for key, label in options.items():
        table.add_row(key, label)
    console.print(table)
    return Prompt.ask("\n[bold cyan]Selecciona una opción[/]", choices=list(options.keys()), default="1")


# ── Ejecución ────────────────────────────────────────────────────────────────

def run_scraper(country: str | None = None, retailers: list[str] | None = None, workers: int = 4):
    """Build args and import main to run inline (same process)."""
    args_list = ["--workers", str(workers)]
    if country:
        args_list += ["--country", country]
    if retailers:
        args_list += ["--retailers"] + retailers

    # patch sys.argv so main.py's argparse picks them up
    old_argv = sys.argv
    sys.argv = ["main.py"] + args_list

    # ensure reports dir
    Path("reports").mkdir(exist_ok=True)

    try:
        import importlib, main as m
        importlib.reload(m)  # re-run with new argv
        exit_code = m.main()
    except SystemExit as e:
        exit_code = e.code
    finally:
        sys.argv = old_argv

    return exit_code


def action_run(country: str | None = None):
    label = {"ES": "España 🇪🇸", "DE": "Alemania 🇩🇪"}.get(country or "", "España 🇪🇸 + Alemania 🇩🇪")
    console.print(Rule(f"[bold cyan]Iniciando scraping · {label}[/]"))

    workers = int(Prompt.ask("Hilos en paralelo", default="4"))

    import subprocess, sys as _sys
    cmd = [_sys.executable, "main.py", "--workers", str(workers)]
    if country:
        cmd += ["--country", country]

    console.print(f"\n[dim]$ {' '.join(cmd)}[/]\n")
    result = subprocess.run(cmd, cwd=Path(__file__).parent)

    if result.returncode == 0:
        console.print("\n[bold green]✓ Scraping completado.[/]")
        _prompt_open_report()
    else:
        console.print("\n[bold red]✗ El scraper terminó con errores.[/]")


def action_select_retailers():
    console.print(Rule("[bold cyan]Selección de retailers[/]"))

    table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
    table.add_column("#",  width=4)
    table.add_column("Retailer", width=26)
    table.add_column("País", width=6)
    table.add_column("URL")
    for i, (name, meta) in enumerate(SCRAPERS_META.items(), 1):
        flag = "🇪🇸" if meta["country"] == "ES" else "🇩🇪"
        table.add_row(str(i), name, f"{flag} {meta['country']}", meta["url"])
    console.print(table)

    raw = Prompt.ask(
        "Escribe los números separados por coma (ej: [cyan]1,3,5[/])"
    )
    indices = []
    for tok in raw.split(","):
        try:
            idx = int(tok.strip()) - 1
            if 0 <= idx < len(SCRAPERS_META):
                indices.append(idx)
        except ValueError:
            pass

    selected = [list(SCRAPERS_META.keys())[i] for i in indices]
    if not selected:
        console.print("[red]No se seleccionó ningún retailer.[/]")
        return

    console.print(f"\nRetailers seleccionados: [cyan]{', '.join(selected)}[/]")
    import subprocess, sys as _sys
    cmd = [_sys.executable, "main.py", "--retailers"] + selected
    console.print(f"\n[dim]$ {' '.join(cmd)}[/]\n")
    subprocess.run(cmd, cwd=Path(__file__).parent)
    _prompt_open_report()


# ── Ver informe ───────────────────────────────────────────────────────────────

def action_view_report():
    console.print(Rule("[bold cyan]Último informe[/]"))
    json_path = find_latest_report("json")
    if not json_path:
        console.print("[yellow]No hay informes generados todavía. Ejecuta el scraper primero.[/]")
        return

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    if not data:
        console.print("[yellow]El informe está vacío.[/]")
        return

    # Summary table
    summary: dict[str, dict] = {}
    for p in data:
        r = summary.setdefault(p["retailer"], {
            "country": p["country"], "total": 0, "ok": 0, "fail": 0, "unk": 0,
        })
        r["total"] += 1
        c = p.get("compliant")
        if c is True:   r["ok"]   += 1
        elif c is False: r["fail"] += 1
        else:            r["unk"]  += 1

    t = Table(title=f"Resumen · {json_path.name}", box=box.ROUNDED, border_style="cyan")
    t.add_column("Retailer",       style="bold")
    t.add_column("País",           width=5)
    t.add_column("Total",          justify="right")
    t.add_column("✅ OK",          justify="right", style="green")
    t.add_column("❌ Incumple",    justify="right", style="red")
    t.add_column("❓ Desconocido", justify="right", style="yellow")

    for name, s in sorted(summary.items(), key=lambda x: -x[1]["fail"]):
        flag = "🇪🇸" if s["country"] == "ES" else "🇩🇪"
        t.add_row(
            name,
            f"{flag} {s['country']}",
            str(s["total"]),
            str(s["ok"]),
            f"[bold]{s['fail']}[/bold]" if s["fail"] else "0",
            str(s["unk"]),
        )
    console.print(t)

    # Non-compliant detail
    violations = [p for p in data if p.get("compliant") is False]
    if violations:
        console.print(f"\n[bold red]── {len(violations)} productos fuera de política ──[/]")
        vt = Table(box=box.SIMPLE_HEAD, border_style="red")
        vt.add_column("País",       width=4)
        vt.add_column("Retailer",   width=24)
        vt.add_column("Producto",   width=38)
        vt.add_column("Precio",     justify="right", width=10)
        vt.add_column("PVP oficial",justify="right", width=12)
        vt.add_column("Descuento",  justify="right", width=10)
        vt.add_column("URL",        no_wrap=False, max_width=50)

        for p in sorted(violations, key=lambda x: x.get("discount_pct") or 0, reverse=True):
            flag = "🇪🇸" if p["country"] == "ES" else "🇩🇪"
            disc = p.get("discount_pct")
            vt.add_row(
                flag,
                p["retailer"],
                p["product_name"][:36],
                f"€{p['price']:.2f}",
                f"€{p['official_price']:.2f}",
                f"[bold red]-{disc:.1f}%[/]" if disc else "?",
                f"[link={p['url']}]{p['url'][:60]}[/link]",
            )
        console.print(vt)
    else:
        console.print("\n[bold green]✓ Todos los productos cumplen la política de precios.[/]")

    console.print(f"\n[dim]Informe completo: {json_path.resolve()}[/]")


# ── Carpeta de informes ───────────────────────────────────────────────────────

def action_open_reports():
    reports_dir = Path("reports").resolve()
    if not reports_dir.exists() or not list(reports_dir.glob("*")):
        console.print("[yellow]La carpeta reports/ está vacía.[/]")
        return
    files = sorted(reports_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
    console.print(f"\n[bold]Informes disponibles[/] en [cyan]{reports_dir}[/]\n")
    for f in files[:15]:
        mtime = datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
        size = f"{f.stat().st_size / 1024:.0f} KB"
        console.print(f"  [cyan]{f.name:<45}[/]  {size:>8}  [dim]{mtime}[/]")
    import subprocess, platform
    if Confirm.ask("\n¿Abrir la carpeta en el explorador de archivos?", default=False):
        if platform.system() == "Darwin":
            subprocess.run(["open", str(reports_dir)])
        elif platform.system() == "Windows":
            subprocess.run(["explorer", str(reports_dir)])
        else:
            subprocess.run(["xdg-open", str(reports_dir)])


# ── Configurar precios ────────────────────────────────────────────────────────

def action_configure_prices():
    console.print(Rule("[bold cyan]Gestión de precios oficiales[/]"))
    from bover_scraper.official_prices import OFFICIAL_PRICES
    console.print(f"  Productos en catálogo actual: [bold cyan]{len(OFFICIAL_PRICES)}[/]")
    console.print()

    options = {
        "1": "Ver todos los precios actuales",
        "2": "Importar precios desde CSV  (columnas: product_name, price)",
        "3": "Buscar un producto",
        "0": "Volver",
    }
    for k, v in options.items():
        console.print(f"  [cyan]{k}[/]  {v}")

    choice = Prompt.ask("Opción", choices=list(options.keys()), default="0")

    if choice == "1":
        t = Table(box=box.SIMPLE_HEAD)
        t.add_column("Producto", width=40)
        t.add_column("PVP oficial (€)", justify="right")
        for k, v in sorted(OFFICIAL_PRICES.items()):
            t.add_row(k, f"{v:.2f}")
        console.print(t)

    elif choice == "2":
        csv_path = Prompt.ask("Ruta al fichero CSV")
        if not Path(csv_path).exists():
            console.print("[red]Fichero no encontrado.[/]")
            return
        import subprocess, sys as _sys
        result = subprocess.run([_sys.executable, "update_prices.py", csv_path])
        if result.returncode == 0:
            console.print("[green]Precios generados. Revisa bover_scraper/official_prices_new.py[/]")

    elif choice == "3":
        query = Prompt.ask("Nombre a buscar").lower()
        matches = {k: v for k, v in OFFICIAL_PRICES.items() if query in k}
        if matches:
            t = Table(box=box.SIMPLE_HEAD)
            t.add_column("Producto", width=40)
            t.add_column("PVP (€)", justify="right")
            for k, v in sorted(matches.items()):
                t.add_row(k, f"{v:.2f}")
            console.print(t)
        else:
            console.print(f"[yellow]Sin resultados para '{query}'[/]")


# ── Estado de retailers ───────────────────────────────────────────────────────

def action_status():
    console.print(Rule("[bold cyan]Estado de retailers[/]"))
    t = Table(box=box.ROUNDED, border_style="cyan")
    t.add_column("#",        width=4, justify="right")
    t.add_column("Retailer", width=26)
    t.add_column("País",     width=6)
    t.add_column("URL")
    t.add_column("Tecnología", width=16)

    tech = {
        "LightingSpain": "Playwright",
        "MyLightShop": "Playwright",
        "LaTiendaDeIluminacion": "Playwright",
        "Lampara.es": "Playwright",
        "Light11": "Playwright",
        "GetLight": "Playwright",
        "Prediger": "Playwright",
        "Reuter": "Playwright",
    }
    for i, (name, meta) in enumerate(SCRAPERS_META.items(), 1):
        flag = "🇪🇸" if meta["country"] == "ES" else "🇩🇪"
        t.add_row(str(i), name, f"{flag} {meta['country']}", meta["url"], tech.get(name, "HTTP"))
    console.print(t)
    console.print(
        "\n[dim]Para añadir un retailer nuevo: crea un fichero en "
        "bover_scraper/scrapers/ heredando PlaywrightScraper y "
        "añádelo a scrapers/__init__.py[/]"
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _prompt_open_report():
    json_path = find_latest_report("json")
    xlsx_path = find_latest_report("xlsx")
    if json_path or xlsx_path:
        console.print()
        if Confirm.ask("¿Ver el resumen del informe ahora?", default=True):
            action_view_report()


# ── Main loop ─────────────────────────────────────────────────────────────────

def main():
    while True:
        clear()
        header()
        choice = menu_main()

        console.print()
        if choice == "1":
            action_run()
        elif choice == "2":
            action_run(country="ES")
        elif choice == "3":
            action_run(country="DE")
        elif choice == "4":
            action_select_retailers()
        elif choice == "5":
            action_view_report()
        elif choice == "6":
            action_open_reports()
        elif choice == "7":
            action_configure_prices()
        elif choice == "8":
            action_status()
        elif choice == "0":
            console.print("[dim]Hasta luego.[/]")
            break

        if choice != "0":
            console.print()
            Prompt.ask("[dim]Pulsa Enter para volver al menú[/]", default="")


if __name__ == "__main__":
    main()
