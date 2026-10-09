"""
Construye y ejecuta el `docker run ... zap-full-scan.py` para un
dominio, a partir de la configuración que llega desde la interfaz.
Es la versión parametrizada de la lógica de nuevolotes.sh original:
mismo manejo de exit codes, mismo naming de salida, pero con todos
los diales configurables desde fuera en vez de fijos en el script.

Nota sobre rutas (Docker-outside-of-Docker):
Este backend corre dentro de SU PROPIO contenedor y lanza contenedores
ZAP "hermanos" a través del socket de Docker del host montado en
/var/run/docker.sock. Cuando este proceso pide `docker run -v X:...`,
el X lo interpreta el daemon de Docker del HOST, no este contenedor.
Por eso HOST_DATA_DIR (la ruta real en el host, ver docker-compose.yml)
y RESULTS_DIR (la ruta dentro de este contenedor) son dos strings
distintos que apuntan al mismo directorio físico.
"""

import asyncio
import os
import re
import shutil
import time
from pathlib import Path

from zap_params import flat_params

ZAP_IMAGE = os.environ.get("ZAP_IMAGE", "ghcr.io/zaproxy/zaproxy:2.17.0")
RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", "/data/results"))
HOST_DATA_DIR = os.environ.get("HOST_DATA_DIR")  # ruta real en el host

# Resolvemos el binario de docker una sola vez al importar el módulo.
# Preferimos "docker" (el nombre correcto, instalado por el Dockerfile
# a partir del CLI estático oficial). Si en algún entorno solo existe
# "docker.io" (paquete apt de Debian sin el alias creado por
# update-alternatives), caemos en él como red de seguridad para no
# repetir el mismo fallo silencioso.
DOCKER_BIN = shutil.which("docker") or shutil.which("docker.io")

EXIT_MEANING = {
    0: "ok",
    1: "fail",
    2: "warn",
    3: "error",
    124: "timeout",
}
EXIT_LABEL = {
    "ok": "Sin FAILs ni WARNs",
    "fail": "Completado con FAILs",
    "warn": "Completado con WARNs",
    "error": "Error real de ZAP",
    "timeout": "Timeout controlado",
    "unknown": "Código de salida inesperado",
}


def normalize_target(raw: str) -> str:
    """zap-full-scan.py exige el esquema en -t; si el usuario pega
    dominios pelados (sin http/https), se lo añadimos por defecto."""
    t = raw.strip()
    if t and not re.match(r"^https?://", t, re.IGNORECASE):
        t = f"https://{t}"
    return t


def safe_name(target: str) -> str:
    """Mismo criterio que el script original: quita esquema y barras."""
    name = re.sub(r"^https?://", "", target.strip())
    return name.replace("/", "")


def build_zap_args(config: dict) -> tuple[list[str], list[str]]:
    """
    A partir del diccionario {param_id: valor} devuelve:
      - cli_args: lista de argumentos sueltos para la CLI (-a, -I, -m 11...)
      - z_parts: lista de trozos "-config clave=valor" para meter dentro de -z
    Los parámetros con flag "__algo__" los gestiona el backend (no son de ZAP).
    """
    cli_args: list[str] = []
    z_parts: list[str] = ["-addonupdate.disable=true"]

    ajax_on = bool(config.get("ajax_spider", False))

    for p in flat_params():
        value = config.get(p["id"], p["default"])

        if p["flag"].startswith("__"):
            continue  # concurrency / hard_timeout: los usa jobs.py, no ZAP

        if p["id"].startswith("ajax_") and p["id"] != "ajax_spider" and not ajax_on:
            continue  # ajustes de Ajax Spider solo si el propio Ajax Spider está activo

        if p["kind"] == "cli_flag":
            if value:
                cli_args.append(p["flag"])
        elif p["kind"] == "cli_value":
            cli_args += [p["flag"], str(value)]
        elif p["kind"] == "zap_config":
            z_parts.append(f"-config {p['flag']}={value}")

    return cli_args, z_parts


def build_command(target: str, config: dict, run_ts: str) -> list[str]:
    name = safe_name(target)
    vol_source = HOST_DATA_DIR or str(RESULTS_DIR.parent)
    cli_args, z_parts = build_zap_args(config)

    return [
        DOCKER_BIN or "docker", "run", "--rm", "-t",
        "--user", "root",
        "-v", f"{vol_source}:/zap/wrk:rw",
        "-v", "zap_dashboard_zap_home:/root/.ZAP",
        ZAP_IMAGE,
        "zap-full-scan.py",
        "-t", target,
        *cli_args,
        "-z", " ".join(z_parts),
        "-J", f"/zap/wrk/results/{run_ts}/{name}.json",
        "-r", f"/zap/wrk/results/{run_ts}/{name}.html",
    ]


async def run_scan(target: str, config: dict, run_ts: str) -> dict:
    name = safe_name(target)
    out_dir = RESULTS_DIR / run_ts
    out_dir.mkdir(parents=True, exist_ok=True)
    log_path = out_dir / f"{name}.log"

    cmd = build_command(target, config, run_ts)
    timeout_s = int(config.get("hard_timeout", 2800))

    start = time.time()
    rc = 3
    with open(log_path, "w") as logf:
        logf.write(f"[*] Escaneando {target}\n[*] Comando: {' '.join(cmd)}\n\n")
        logf.flush()
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=logf, stderr=asyncio.subprocess.STDOUT
            )
            try:
                rc = await asyncio.wait_for(proc.wait(), timeout=timeout_s)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                rc = 124
        except FileNotFoundError:
            logf.write(
                f"[ERROR] No se encontró un binario de Docker utilizable "
                f"dentro del contenedor del backend (se buscó 'docker' y "
                f"'docker.io' en PATH, resuelto a: {DOCKER_BIN!r}). "
                "Revisa el Dockerfile / el socket montado.\n"
            )
            rc = 3

    status = EXIT_MEANING.get(rc, "unknown")
    return {
        "target": target,
        "safe_name": name,
        "exit_code": rc,
        "status": status,
        "status_label": EXIT_LABEL.get(status, "Código inesperado"),
        "duration_s": round(time.time() - start, 1),
        "log_file": f"/results/{run_ts}/{name}.log",
        "json_report": f"/results/{run_ts}/{name}.json",
        "html_report": f"/results/{run_ts}/{name}.html",
    }
