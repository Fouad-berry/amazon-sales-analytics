"""
pipeline.py — Orchestrateur ELT
Extract → Load (raw) → Transform → Load (staging + intermediate + marts)
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path

os.makedirs("logs", exist_ok=True)

LOG_FILE = f"logs/pipeline_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [PIPELINE] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE),
    ],
)
log = logging.getLogger(__name__)

BANNER = """
╔══════════════════════════════════════════════════════╗
║     AMAZON SALES — ANALYTICS ENGINEER PIPELINE      ║
║               ELT : E → L(raw) → T → L(marts)      ║
╚══════════════════════════════════════════════════════╝"""


def run_pipeline():
    start = datetime.utcnow()
    print(BANNER)
    log.info(f"Démarrage : {start.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    log.info(f"Log file  : {LOG_FILE}")

    steps = [
        ("STEP 1/3 — EXTRACT",           "elt.extract.extract",   "run"),
        ("STEP 2/3 — TRANSFORM",          "elt.transform.transform","run"),
        ("STEP 3/3 — LOAD (ALL LAYERS)",  "elt.load.load",          "run"),
    ]

    for label, module_path, func_name in steps:
        log.info(f"\n{'─'*54}\n  {label}\n{'─'*54}")
        t0 = datetime.utcnow()
        try:
            import importlib
            mod = importlib.import_module(module_path)
            getattr(mod, func_name)()
            elapsed = (datetime.utcnow() - t0).total_seconds()
            log.info(f"  ✓ {label} terminé en {elapsed:.1f}s")
        except Exception as e:
            log.error(f"  ✗ ERREUR dans {label}: {e}", exc_info=True)
            sys.exit(1)

    total = (datetime.utcnow() - start).total_seconds()
    log.info(f"""
╔══════════════════════════════════════════════════════╗
║  PIPELINE TERMINÉ EN {total:.1f}s
║  Marts disponibles dans : data/mart/
║  DB SQLite              : data/amazon_analytics.db
╚══════════════════════════════════════════════════════╝""")


if __name__ == "__main__":
    run_pipeline()