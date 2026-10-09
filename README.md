# V80000-ZAP-Dashboard
🛡️ Dashboard gráfico basado en OWASP ZAP para automatizar auditorías de seguridad web por lotes. Permite configurar visualmente los parámetros de escaneo, con explicaciones de cada opción para facilitar su uso a principiantes. Docker, informes HTML/JSON y ejecución automatizada. 🚧 Próximas mejoras en camino...

# v80000 ZAP Dashboard - FULL EXPLANATION IN ENGLISH

A simple web dashboard for running OWASP ZAP scans against multiple websites using Docker.

I made this project because I wanted an easier way to work with ZAP without having to write long commands every time I needed to scan a list of domains. Instead of doing everything in the terminal, you can set up your scans from a web page and let the dashboard handle the rest.

It's also designed with beginners in mind. Every setting has an information button that explains what it does and when you might want to change it. You can learn how the different ZAP options work while using the tool, rather than just changing values without knowing what they mean.

The dashboard uses OWASP ZAP underneath. It doesn't replace ZAP or include every option available in it; it gives you graphical access to a useful set of its full-scan settings.

## What you can do

- Scan several domains in one batch, either by pasting URLs or loading a `.txt` file.
- Configure supported ZAP options from the browser, without writing the commands yourself.
- Read a short explanation and recommendation for each setting.
- Adjust spider crawling, active scan settings, request delays and scan limits.
- Enable Ajax Spider for websites that need browser-based crawling.
- Choose how many scans run at the same time and set a timeout for each target.
- Check the status of your scans and open the generated HTML and JSON reports.
- Keep scan logs and previous reports on disk, even after restarting the dashboard.

The interface is currently in Spanish.

## Scan settings

The dashboard groups its settings into a few sections to keep things organised:

**Spider:** crawling time, maximum depth and number of links to follow.

**Active scan:** attack strength, alert threshold, threads per host, maximum scan duration and delay between requests.

**Ajax Spider:** enable browser-based crawling, choose a headless browser and set the number of browsers.

**Reports and behaviour:** detailed logs, handling of warnings and optional alpha scan rules.

**Batch:** number of scans running in parallel and a hard timeout for each target.

You don't have to understand every option before starting. That's the main reason I added the information panels: you can see what a setting changes before deciding whether to use it.

## Installation

You'll need Docker and Docker Compose installed and working on your machine. Port `8000` should also be available, unless you change it.

Clone the repository and start it:

```bash
git clone https://github.com/v80000/v80000-ZAP-Dashboard.git
cd v80000-ZAP-Dashboard
docker compose up --build -d
```

Then open `http://localhost:8000` in your browser.

The first build may take a little longer because Docker needs to build the dashboard image. ZAP also needs its Docker image when you run scans.

If you want to use a different port, for example `8080`, start it with:

```bash
DASHBOARD_PORT=8080 docker compose up --build -d
```

To stop the dashboard:

```bash
docker compose down
```

These commands use the standalone `docker-compose.yml` inside this repository. If you're running it alongside another project, use the Compose file for that setup instead.

## How to use it

Open the dashboard and paste the websites you want to scan, one URL per line. You can also upload a text file containing the list. If you leave out `http://` or `https://`, the dashboard assumes HTTPS.

Next, check the available settings. You can leave the defaults as they are or open the information buttons to understand and adjust them. When you're ready, click **Lanzar lote** to start the batch.

The dashboard will run a separate ZAP scan for each target. You can follow the progress and access the reports once they have been generated.

Remember that a ZAP full scan performs active security tests. Use this only on websites you own or have clear permission to test.

## Reports

The reports are saved in `data/results/`, with a folder for each batch:

```text
data/results/
    2026-10-09_12-00-00/
        example.com.html
        example.com.json
        example.com.log
```

The HTML file is useful for reading the results, the JSON file can be used for further analysis, and the log helps you check what happened during the scan.

The dashboard can find previous report folders after a restart. However, scans that were running at the time are not automatically resumed.

Don't upload real scan reports to a public repository. They may contain information about the websites you've tested.

## How it works

The frontend is built with HTML, CSS and JavaScript, and the backend uses Python and FastAPI.

Everything runs in Docker. The dashboard connects to the Docker service on your machine and starts temporary OWASP ZAP containers to carry out the scans. The results are then saved to the `data/results/` folder so you can access them later.

The main files are:

- `backend/main.py`: web API and dashboard endpoints.
- `backend/zap_params.py`: available settings, default values and help text.
- `backend/scanner.py`: builds and runs the ZAP commands.
- `backend/jobs.py`: manages scan batches and their status.
- `frontend/`: the web interface.
- `docker-compose.yml`: starts the dashboard with Docker.

One thing I wanted from the start was to keep the configuration in one place. The same parameter definitions are used to build the interface and to prepare the ZAP commands, making the project easier to maintain and expand.

## Security notes

This dashboard is intended for authorised security testing. Active scans can send a lot of requests and may affect the website being tested. Make sure you have permission and use settings that are appropriate for the target.

The dashboard doesn't currently have user authentication. It also uses the host's Docker socket to start scan containers, which gives the backend powerful access to the machine. Because of that, don't expose it directly to the internet or an untrusted network.

For local use, you can restrict the published port in `docker-compose.yml` to your own computer:

```yaml
ports:
  - "127.0.0.1:${DASHBOARD_PORT:-8000}:8000"
```

This is a recommended change, not the default configuration in the repository.

## Coming soon

I want to keep improving the project over time. Some things I'd like to add are authenticated scans, more report formats, support for more ZAP settings and general improvements to the interface.

These features aren't included yet. I'll add them as I develop and test them.

## Feedback

If you find a bug or have an idea that could make the dashboard better, feel free to open an issue. Suggestions are welcome, especially from people who are learning ZAP and find something confusing or difficult to use.

Created by [v80000](https://github.com/v80000).

## License

There is currently no license file included in this project. I'll update this section if I add one.
