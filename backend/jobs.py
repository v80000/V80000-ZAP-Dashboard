"""
Cola de trabajos en memoria: cada 'batch' (lote) tiene un run_ts
(timestamp de carpeta, igual que en el script original) y un estado
por dominio. El historial también se reconstruye leyendo el disco,
así que sobrevive a un reinicio del backend aunque el estado en vivo
del propio proceso no.
"""

import asyncio
import time
from datetime import datetime
from pathlib import Path

import scanner

RESULTS_DIR = scanner.RESULTS_DIR

_jobs: dict[str, dict] = {}


def new_run_ts() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


async def start_batch(targets: list[str], config: dict) -> str:
    run_ts = new_run_ts()
    concurrency = max(1, int(config.get("concurrency", 1)))

    _jobs[run_ts] = {
        "run_ts": run_ts,
        "config": config,
        "concurrency": concurrency,
        "targets": {t: {"target": t, "status": "pending"} for t in targets},
        "started_at": time.time(),
        "finished_at": None,
    }

    asyncio.create_task(_run_batch(run_ts, targets, config, concurrency))
    return run_ts


async def _run_batch(run_ts: str, targets: list[str], config: dict, concurrency: int):
    sem = asyncio.Semaphore(concurrency)

    async def _one(target: str):
        async with sem:
            _jobs[run_ts]["targets"][target]["status"] = "running"
            try:
                result = await scanner.run_scan(target, config, run_ts)
                _jobs[run_ts]["targets"][target].update(result)
            except Exception as exc:  # no tumbar el resto del lote por un fallo puntual
                _jobs[run_ts]["targets"][target].update(
                    {"status": "error", "status_label": str(exc)}
                )

    await asyncio.gather(*(_one(t) for t in targets))
    _jobs[run_ts]["finished_at"] = time.time()


def get_job(run_ts: str) -> dict | None:
    if run_ts in _jobs:
        return _jobs[run_ts]

    # el backend se ha reiniciado: reconstruir un resumen leyendo el disco
    d = RESULTS_DIR / run_ts
    if not d.exists():
        return None
    targets = {}
    for f in sorted(d.glob("*.json")):
        targets[f.stem] = {
            "target": f.stem,
            "status": "done",
            "json_report": f"/results/{run_ts}/{f.name}",
            "html_report": f"/results/{run_ts}/{f.stem}.html",
        }
    return {"run_ts": run_ts, "targets": targets, "from_disk": True}


def list_jobs() -> list[dict]:
    seen = set(_jobs.keys())
    out = list(_jobs.values())

    if RESULTS_DIR.exists():
        for d in RESULTS_DIR.iterdir():
            if d.is_dir() and d.name not in seen:
                out.append({"run_ts": d.name, "targets": {}, "from_disk": True})

    return sorted(out, key=lambda j: j["run_ts"], reverse=True)
