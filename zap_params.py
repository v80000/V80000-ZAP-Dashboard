"""
Catálogo de parámetros configurables de zap-full-scan.py.

Esto es la única fuente de verdad: el frontend construye el formulario
leyendo GET /api/params (que sirve PARAM_GROUPS tal cual), y el backend
usa esta misma estructura en scanner.py para construir el comando real
de `docker run ... zap-full-scan.py`. Si añades un parámetro aquí,
aparece solo en la interfaz sin tocar nada más.

Cada parámetro tiene:
  id        clave interna (así viaja en el JSON de configuración)
  flag      el flag de CLI ("-a", "-I"...) o la clave de config de ZAP
            ("scanner.attackStrength") según el tipo
  kind      "cli_flag"   -> interruptor on/off que añade un flag suelto (-a, -d, -I...)
            "cli_value"  -> flag que lleva un valor (-m 11, -T 9...)
            "zap_config" -> se traduce a "-config <flag>=<valor>" dentro del -z
  type      "bool" | "int" | "select"
  default   valor por defecto
  label     etiqueta corta del campo
  help      texto del desplegable de ayuda: qué hace, en plano
  recommend una línea de orientación práctica sobre cuándo tocarlo

Los flags que empiezan por "__" (ej. "__timeout__") no se pasan a ZAP:
los gestiona el propio backend (timeout duro del proceso, nº de
escaneos en paralelo).

Cobertura: esto incluye los flags de zap-full-scan.py que cambian el
comportamiento real del rastreo/ataque, más las claves scanner.*,
spider.* y ajaxSpider.* más usadas para afinarlo. No incluye flags
puramente de fontanería (rutas de informe, ficheros de contexto para
login, puerto de escucha...) que el backend ya gestiona solo o que
requieren un fichero de contexto aparte (autenticación) — eso queda
para una siguiente vuelta.
"""

PARAM_GROUPS = [
    {
        "id": "spider",
        "label": "Rastreo (spider)",
        "description": "Cómo descubre ZAP las páginas del sitio antes de atacarlas.",
        "params": [
            {
                "id": "spider_minutes",
                "flag": "-m",
                "kind": "cli_value",
                "type": "int",
                "default": 11,
                "min": 1,
                "max": 180,
                "label": "Minutos de rastreo",
                "help": "Tiempo máximo que ZAP pasa recorriendo enlaces antes de pasar al ataque activo.",
                "recommend": "Sitios pequeños: 5-10 min. Sitios grandes con muchas subpáginas: súbelo o el rastreo se quedará corto y el ataque no llegará a todo.",
            },
            {
                "id": "spider_max_depth",
                "flag": "spider.maxDepth",
                "kind": "zap_config",
                "type": "int",
                "default": 5,
                "min": 0,
                "max": 20,
                "label": "Profundidad máxima",
                "help": "Cuántos clics de distancia desde la portada está dispuesto a llegar el rastreador. 0 = sin límite.",
                "recommend": "5 cubre bien la mayoría de webs corporativas pequeñas sin dispararse el tiempo.",
            },
            {
                "id": "spider_max_children",
                "flag": "spider.maxChildren",
                "kind": "zap_config",
                "type": "int",
                "default": 80,
                "min": 0,
                "max": 2000,
                "label": "Máx. enlaces por página",
                "help": "Cuántos enlaces hijos sigue el rastreador desde una misma página. 0 = sin límite.",
                "recommend": "Bájalo en catálogos o listados enormes para que el rastreo no se eternice ahí.",
            },
            {
                "id": "ajax_spider",
                "flag": "-j",
                "kind": "cli_flag",
                "type": "bool",
                "default": False,
                "label": "Rastreo con navegador (Ajax Spider)",
                "help": "Suma al rastreo normal un navegador real (headless) que pulsa botones y ejecuta JavaScript, encontrando rutas que una app moderna (React, Vue...) esconde del rastreador tradicional.",
                "recommend": "Actívalo en SPAs o sitios muy dinámicos. Es notablemente más lento — en catálogos estáticos no compensa.",
            },
        ],
    },
    {
        "id": "attack",
        "label": "Ataque activo",
        "description": "Cómo de agresivo es ZAP enviando payloads reales contra el sitio. Esta es la parte que realmente 'ataca'.",
        "params": [
            {
                "id": "attack_strength",
                "flag": "scanner.attackStrength",
                "kind": "zap_config",
                "type": "select",
                "default": "MEDIUM",
                "label": "Intensidad del ataque",
                "options": [
                    {"value": "LOW", "label": "Baja", "help": "Menos variantes de payload por regla. Más rápido; se le pueden escapar casos límite."},
                    {"value": "MEDIUM", "label": "Media", "help": "El equilibrio por defecto de ZAP entre cobertura y tiempo."},
                    {"value": "HIGH", "label": "Alta", "help": "Muchas más variantes por regla. Más fiable, bastante más lento y más ruido en los logs del sitio objetivo."},
                    {"value": "INSANE", "label": "Extrema", "help": "Prueba casi todo lo que sabe cada regla. Pensada para laboratorio: puede tardar horas y saturar el sitio."},
                ],
                "recommend": "HIGH es razonable para una auditoría formal. Evita INSANE contra un sitio en producción.",
            },
            {
                "id": "alert_threshold",
                "flag": "scanner.alertThreshold",
                "kind": "zap_config",
                "type": "select",
                "default": "MEDIUM",
                "label": "Umbral de confianza para alertar",
                "options": [
                    {"value": "LOW", "label": "Bajo", "help": "Reporta hasta indicios débiles. Más hallazgos, más falsos positivos que descartar a mano."},
                    {"value": "MEDIUM", "label": "Medio", "help": "El equilibrio por defecto entre ruido y cobertura."},
                    {"value": "HIGH", "label": "Alto", "help": "Solo reporta cuando ZAP está muy seguro. Informe más limpio, pero puede omitir hallazgos reales."},
                ],
                "recommend": "LOW si vas a revisar el informe tú mismo y no quieres dejarte nada. HIGH si lo va a leer alguien sin tiempo para filtrar ruido.",
            },
            {
                "id": "thread_per_host",
                "flag": "scanner.threadPerHost",
                "kind": "zap_config",
                "type": "int",
                "default": 4,
                "min": 1,
                "max": 20,
                "label": "Hilos por objetivo",
                "help": "Cuántas peticiones de ataque en paralelo se envían al mismo sitio.",
                "recommend": "Súbelo para ir más rápido en sitios que aguanten carga; bájalo a 1-2 en hosting modesto para no tumbarlo.",
            },
            {
                "id": "max_scan_duration",
                "flag": "scanner.maxScanDurationInMins",
                "kind": "zap_config",
                "type": "int",
                "default": 25,
                "min": 0,
                "max": 300,
                "label": "Duración máx. del ataque (min)",
                "help": "Corta el ataque activo a los N minutos aunque no haya terminado. 0 = sin límite.",
                "recommend": "Ponle techo siempre que escanees por lotes — si no, un sitio grande puede acaparar todo el tiempo del lote.",
            },
            {
                "id": "delay_in_ms",
                "flag": "scanner.delayInMs",
                "kind": "zap_config",
                "type": "int",
                "default": 0,
                "min": 0,
                "max": 5000,
                "label": "Pausa entre peticiones (ms)",
                "help": "Espera artificial entre cada petición de ataque.",
                "recommend": "Súbelo si el sitio tiene rate limiting y quieres evitar bloqueos o falsos negativos por baneo a mitad de escaneo.",
            },
        ],
    },
    {
        "id": "ajax",
        "label": "Ajax Spider — ajustes",
        "description": "Solo se aplican si activas 'Rastreo con navegador' arriba.",
        "params": [
            {
                "id": "ajax_browser",
                "flag": "ajaxSpider.browserId",
                "kind": "zap_config",
                "type": "select",
                "default": "firefox-headless",
                "label": "Navegador",
                "options": [
                    {"value": "firefox-headless", "label": "Firefox (headless)", "help": "El más probado dentro de la imagen Docker de ZAP."},
                    {"value": "chrome-headless", "label": "Chrome (headless)", "help": "Alternativa si el sitio se comporta distinto en Chrome."},
                ],
                "recommend": "Déjalo en Firefox salvo que el sitio falle específicamente con ese motor.",
            },
            {
                "id": "ajax_num_browsers",
                "flag": "ajaxSpider.numberOfBrowsers",
                "kind": "zap_config",
                "type": "int",
                "default": 2,
                "min": 1,
                "max": 8,
                "label": "Navegadores en paralelo",
                "help": "Cuántas instancias de navegador headless usa el rastreo Ajax a la vez. Más = más rápido, más RAM.",
                "recommend": "2 va bien en la mayoría de máquinas. Súbelo solo si sobra RAM.",
            },
        ],
    },
    {
        "id": "reporting",
        "label": "Comportamiento e informe",
        "description": "Cómo se comporta el propio proceso de escaneo.",
        "params": [
            {
                "id": "ignore_warn",
                "flag": "-I",
                "kind": "cli_flag",
                "type": "bool",
                "default": True,
                "label": "No fallar por warnings",
                "help": "El proceso devuelve normalmente un código de error si ZAP encuentra avisos (WARN). Con esto activo, solo falla ante errores reales de ZAP.",
                "recommend": "Actívalo para lotes automatizados — si no, un sitio con hallazgos menores puede parar el resto del lote.",
            },
            {
                "id": "debug",
                "flag": "-d",
                "kind": "cli_flag",
                "type": "bool",
                "default": True,
                "label": "Logs detallados",
                "help": "Vuelca mensajes de debug en el log del contenedor — útil para diagnosticar un escaneo que se comporta raro.",
                "recommend": "Déjalo activado mientras pruebas el dashboard; puedes apagarlo cuando ya confíes en tu configuración.",
            },
            {
                "id": "include_alpha",
                "flag": "-a",
                "kind": "cli_flag",
                "type": "bool",
                "default": False,
                "label": "Incluir reglas alpha",
                "help": "Suma las reglas de escaneo todavía en fase alpha: menos maduras y con más falsos positivos, pero cubren hallazgos más recientes.",
                "recommend": "Solo si quieres la cobertura más amplia posible y estás dispuesto a filtrar más ruido a mano.",
            },
        ],
    },
    {
        "id": "batch",
        "label": "Lote",
        "description": "Cómo se procesa la lista de dominios. Estos dos no son flags de ZAP — los gestiona el propio dashboard.",
        "params": [
            {
                "id": "concurrency",
                "flag": "__concurrency__",
                "kind": "cli_value",
                "type": "int",
                "default": 1,
                "min": 1,
                "max": 10,
                "label": "Dominios en paralelo",
                "help": "Cuántos escaneos corren a la vez. Cada uno es un contenedor ZAP independiente.",
                "recommend": "1-2 en un portátil normal. Cada escaneo en paralelo multiplica el uso de CPU/RAM — súbelo solo si el host lo aguanta.",
            },
            {
                "id": "hard_timeout",
                "flag": "__timeout__",
                "kind": "cli_value",
                "type": "int",
                "default": 2800,
                "min": 60,
                "max": 10800,
                "label": "Timeout duro por dominio (seg)",
                "help": "Si un escaneo individual supera este tiempo, se corta a la fuerza. Es el límite de seguridad por fuera de ZAP, independiente de la 'duración máx. del ataque'.",
                "recommend": "Déjalo bastante por encima de (minutos de rastreo + duración máx. del ataque) para no cortar escaneos legítimos a medias.",
            },
        ],
    },
]


def flat_params():
    """Itera todos los parámetros de todos los grupos, uno a uno."""
    for group in PARAM_GROUPS:
        for p in group["params"]:
            yield p


def defaults() -> dict:
    """Config por defecto: {id: valor_por_defecto} para todos los parámetros."""
    return {p["id"]: p["default"] for p in flat_params()}
