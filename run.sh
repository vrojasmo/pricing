#!/bin/bash
# ─────────────────────────────────────────────────────────────
#  Bover Price Compliance – arranque rápido
#  Uso:
#    ./run.sh              → menú interactivo
#    ./run.sh full         → scraping completo ES + DE
#    ./run.sh es           → solo España
#    ./run.sh de           → solo Alemania
#    ./run.sh report       → ver último informe
#    ./run.sh help         → mostrar ayuda
# ─────────────────────────────────────────────────────────────

set -e
cd "$(dirname "$0")"

# Comprobación de dependencias
if ! python3 -c "import rich" 2>/dev/null; then
    echo "Instalando dependencias..."
    pip3 install -r requirements.txt -q
fi

CMD=${1:-"menu"}

case "$CMD" in
    menu)
        python3 bover_cli.py
        ;;
    full)
        python3 main.py "${@:2}"
        ;;
    es)
        python3 main.py --country ES "${@:2}"
        ;;
    de)
        python3 main.py --country DE "${@:2}"
        ;;
    report)
        python3 -c "
from bover_cli import action_view_report
action_view_report()
"
        ;;
    test)
        python3 -m pytest tests/ -v
        ;;
    help|*)
        echo ""
        echo "  Bover Price Compliance Scraper"
        echo ""
        echo "  Uso:"
        echo "    ./run.sh              Menú interactivo (recomendado)"
        echo "    ./run.sh full         Scraping completo ES + DE"
        echo "    ./run.sh es           Solo España"
        echo "    ./run.sh de           Solo Alemania"
        echo "    ./run.sh report       Ver último informe"
        echo "    ./run.sh test         Ejecutar tests"
        echo ""
        echo "  Opciones avanzadas (se pasan a main.py):"
        echo "    --workers N           Hilos paralelos (default 4)"
        echo "    --retailers R1 R2     Solo esos retailers"
        echo "    --output DIR          Carpeta de salida"
        echo "    --no-excel            Sin Excel"
        echo "    --prices file.csv     Precios oficiales desde CSV"
        echo ""
        ;;
esac
