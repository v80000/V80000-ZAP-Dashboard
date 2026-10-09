import json
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import jobs
import scanner
from zap_params import PARAM_GROUPS, defaults

app = FastAPI(title="ZAP Batch Dashboard")

RESULTS_DIR = scanner.RESULTS_DIR
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Los informes HTML/JSON quedan servidos tal cual en /results/<run_ts>/<archivo>
app.mount("/results", StaticFiles(directory=str(RESULTS_DIR)), name="results")


class ScanRequest(BaseModel):
    targets: list[str]
    config: dict = {}


@app.get("/api/params")
def api_params():
    """El frontend construye el formulario entero a partir de esto."""
    return {"groups": PARAM_GROUPS, "defaults": defaults()}


@app.post("/api/targets/upload")
async def api_upload_targets(file: UploadFile = File(...)):
    content = (await file.read()).decode("utf-8", errors="ignore")
    targets = [
        scanner.normalize_target(line)
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    return {"targets": targets, "count": len(targets)}


@app.post("/api/scan")
async def api_start_scan(req: ScanRequest):
    targets = [
        scanner.normalize_target(t)
        for t in req.targets
        if t.strip() and not t.strip().startswith("#")
    ]
    if not targets:
        return JSONResponse({"error": "No hay dominios en el lote"}, status_code=400)

    config = {**defaults(), **req.config}
    run_ts = await jobs.start_batch(targets, config)
    return {"run_ts": run_ts, "targets": targets, "config": config}


@app.get("/api/jobs")
def api_list_jobs():
    return jobs.list_jobs()


@app.get("/api/jobs/{run_ts}")
def api_get_job(run_ts: str):
    job = jobs.get_job(run_ts)
    if job is None:
        return JSONResponse({"error": "not found"}, status_code=404)
    return job


@app.get("/api/reports/{run_ts}/{name}/summary")
def api_report_summary(run_ts: str, name: str):
    """
    Resumen de alertas por nivel de riesgo a partir del JSON que
    genera ZAP. La forma exacta del JSON puede variar entre versiones
    de ZAP -- si esto devuelve todo a cero, compara las claves con un
    informe real generado por tu instalación y ajusta aquí.
    """
    path = RESULTS_DIR / run_ts / f"{name}.json"
    if not path.exists():
        return JSONResponse({"error": "not found"}, status_code=404)

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError:
        return JSONResponse({"error": "informe JSON ilegible"}, status_code=500)

    counts = {"High": 0, "Medium": 0, "Low": 0, "Informational": 0}
    for site in data.get("site", []):
        for alert in site.get("alerts", []):
            risk = str(alert.get("riskdesc", "")).split(" ")[0]
            if risk in counts:
                instances = alert.get("instances", [])
                counts[risk] += len(instances) if instances else 1

    return {"target": name, "counts": counts}


# Catch-all: sirve el frontend. Tiene que registrarse el último para no
# tapar las rutas /api/* y /results/* de arriba.
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
