FROM python:3.12-slim

# Cliente docker (CLI estático oficial, SIN daemon): este contenedor
# habla con el Docker del host a través del socket montado, para
# lanzar los contenedores ZAP "hermanos" (patrón Docker-outside-of-
# Docker).
#
# Antes se instalaba aquí el paquete apt "docker.io", pero ese paquete
# choca de nombre con un viejo applet de X11 llamado "docker", así que
# Debian NO instala el binario como /usr/bin/docker directamente: lo
# instala como /usr/bin/docker.io y registra el alias "docker" vía
# update-alternatives. En instalaciones mínimas (--no-install-
# recommends) ese symlink puede no llegar a crearse -- el paquete se
# instala "sin errores" pero el comando `docker`, que es literalmente
# lo que ejecuta scanner.py, no existe en el PATH. De ahí el
# FileNotFoundError en tiempo de ejecución aunque el build no falle.
#
# Para evitar esa ambigüedad usamos el binario estático oficial de
# Docker (solo el cliente, documentado por Docker para este mismo
# patrón DooD): https://docs.docker.com/engine/install/binaries/
ARG DOCKER_CLI_VERSION=27.4.1

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

RUN ARCH="$(uname -m)" \
    && case "$ARCH" in \
         x86_64) DOCKER_ARCH=x86_64 ;; \
         aarch64|arm64) DOCKER_ARCH=aarch64 ;; \
         *) echo "Arquitectura no soportada para el CLI de Docker: $ARCH" >&2; exit 1 ;; \
       esac \
    && curl -fsSL "https://download.docker.com/linux/static/stable/${DOCKER_ARCH}/docker-${DOCKER_CLI_VERSION}.tgz" -o /tmp/docker-cli.tgz \
    && tar -xzf /tmp/docker-cli.tgz -C /tmp \
    && mv /tmp/docker/docker /usr/local/bin/docker \
    && chmod +x /usr/local/bin/docker \
    && rm -rf /tmp/docker /tmp/docker-cli.tgz

# Falla el build (no el arranque en producción) si el binario no quedó
# operativo -- así el problema se detecta en `docker compose up --build`.
RUN docker --version

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .
COPY frontend/ /app/frontend/

RUN mkdir -p /data/results
ENV RESULTS_DIR=/data/results

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
