"""Teste de interface do mapa GeoSBS num navegador real (Edge ou Chrome, sem janela).

Uso (na raiz do projeto, depois de `python main.py`):
    pip install -r requirements-dev.txt
    python tests/ui/run_ui_tests.py

O que faz:
1. Copia output/maps/geosbs.html e tests/ui/harness.html para uma pasta temporária
   e serve essa pasta em http://localhost:<porta> (domínio autorizado da chave Esri).
2. Abre o navegador em modo headless pelo protocolo DevTools (CDP), com
   renderização WebGL por software (SwiftShader), e carrega o roteiro harness.html.
3. Compara os resultados com o esperado e termina com código 1 se algo falhar.

Fica fora do `pytest` porque é lento (~2 min) e precisa de navegador instalado.
Use GEOSBS_BROWSER=<caminho do executável> para escolher outro navegador.
"""
from __future__ import annotations

import functools
import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

try:
    import websocket  # websocket-client
except ImportError:
    sys.exit("Instale as dependências de desenvolvimento: pip install -r requirements-dev.txt")

ROOT = Path(__file__).resolve().parents[2]
MAP_FILE = ROOT / "output" / "maps" / "geosbs.html"
HARNESS = Path(__file__).with_name("harness.html")
CANDIDATES = [
    os.environ.get("GEOSBS_BROWSER", ""),
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/microsoft-edge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # sem log de cada requisição no console
        pass


def serve(folder: Path) -> tuple[http.server.ThreadingHTTPServer, int]:
    port = free_port()
    handler = functools.partial(QuietHandler, directory=str(folder))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def run_browser(url: str, timeout_s: int = 240) -> dict:
    exe = next((c for c in CANDIDATES if c and Path(c).exists()), None)
    if not exe:
        sys.exit("Navegador Edge/Chrome não encontrado. Defina GEOSBS_BROWSER.")
    port, profile = free_port(), tempfile.mkdtemp(prefix="geosbs_ui_")
    proc = subprocess.Popen([exe, "--headless=new", f"--remote-debugging-port={port}", f"--user-data-dir={profile}",
                             "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist",
                             "--no-first-run", "--hide-scrollbars", "--window-size=1200,900", "about:blank"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                pages = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json/list"))
                page = next(p for p in pages if p["type"] == "page")
                break
            except Exception:
                time.sleep(0.3)
        else:
            raise RuntimeError("o navegador não abriu a porta de depuração")
        ws = websocket.create_connection(page["webSocketDebuggerUrl"], timeout=60)
        counter = [0]

        def call(method, **params):
            counter[0] += 1
            ws.send(json.dumps({"id": counter[0], "method": method, "params": params}))
            while True:
                msg = json.loads(ws.recv())
                if msg.get("id") == counter[0]:
                    return msg.get("result", {})

        def js(expr):
            return call("Runtime.evaluate", expression=expr, returnByValue=True).get("result", {}).get("value")

        call("Page.navigate", url=url)
        start = time.time()
        while time.time() - start < timeout_s:
            time.sleep(1)
            if js("document.title") == "pronto":
                return json.loads(js("document.getElementById('out').textContent"))
        raise TimeoutError(f"o roteiro não terminou em {timeout_s} s")
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


def checks(r: dict) -> list[tuple[str, bool, object]]:
    total = r.get("totalEstabelecimentos")
    bairros = r.get("bairros")
    return [
        ("mapa inicializa", r.get("pronto") is True, r.get("pronto")),
        ("município inteiro visível ao abrir", r.get("municipioInteiroAoAbrir") is True, r.get("municipioInteiroAoAbrir")),
        ("todos os estabelecimentos visíveis ao abrir", r.get("visiveisAoAbrir") == total, f"{r.get('visiveisAoAbrir')} de {total}"),
        ("navegação contida na região", r.get("navegacaoContida") is True, r.get("navegacaoContida")),
        ("botão ⌂ volta ao município", r.get("botaoVoltarMunicipio") is True, r.get("botaoVoltarMunicipio")),
        ("filtro 'só Saúde'", (r.get("soSaude") or {}).get("obtido") == (r.get("soSaude") or {}).get("esperado"), r.get("soSaude")),
        ("ver mapa de calor", r.get("verCalor") == {"calor": "visible", "pontos": 0}, r.get("verCalor")),
        ("ver marcadores", r.get("verMarcadores") == {"calor": "none", "pontos": total}, r.get("verMarcadores")),
        ("ocultar todas", r.get("ocultarTodas") == 0, r.get("ocultarTodas")),
        ("mostrar todas", r.get("mostrarTodas") == total, r.get("mostrarTodas")),
        ("coroplético de densidade", r.get("coropletico_dens") == bairros, r.get("coropletico_dens")),
        ("coroplético de quantidade", r.get("coropletico_total") == bairros, r.get("coropletico_total")),
        ("coroplético por habitante", r.get("coropletico_hab") == bairros, r.get("coropletico_hab")),
        ("modo satélite", (r.get("base_satelite") or {}).get("satelite") == "visible", r.get("base_satelite")),
        ("modo híbrido com rótulos", r.get("base_hibrido") == {"satelite": "visible", "relevo": "none", "rotulos": "visible"}, r.get("base_hibrido")),
        ("modo relevo", (r.get("base_relevo") or {}).get("relevo") == "visible", r.get("base_relevo")),
        ("modo mapa", (r.get("base_mapa") or {}).get("satelite") == "none", r.get("base_mapa")),
        ("aba Bairros lista todos os bairros", bool(r.get("abaBairros")) and r["abaBairros"]["aberta"]
         and r["abaBairros"]["linhas"] == r["abaBairros"]["bairros"] == bairros,
         f"{(r.get('abaBairros') or {}).get('linhas')} de {bairros}"),
        ("clique na aba Bairros leva ao bairro", (r.get("abaBairros") or {}).get("foiAoBairro") is True,
         (r.get("abaBairros") or {}).get("foiAoBairro")),
        ("camada CNES desligada ao abrir", (r.get("cnes") or {}).get("aoAbrir") == "none", (r.get("cnes") or {}).get("aoAbrir")),
        ("camada CNES mostra todas as unidades", bool(r.get("cnes")) and r["cnes"]["visiveis"] == r["cnes"]["total"] > 0,
         f"{(r.get('cnes') or {}).get('visiveis')} de {(r.get('cnes') or {}).get('total')}"),
        ("CNES na legenda, contagens inalteradas", bool(r.get("cnes")) and r["cnes"]["legenda"] and r["cnes"]["contagensIguais"],
         {k: (r.get("cnes") or {}).get(k) for k in ("legenda", "contagensIguais")}),
        ("popup do CNES (ESF Alpino)", (r.get("cnes") or {}).get("popupAlpino") is True, (r.get("cnes") or {}).get("popupAlpino")),
        ("popup do hospital", r.get("popupHospital") is True, r.get("popupHospital")),
        ("clique no cluster aproxima", r.get("cliqueClusterAproxima") is True, r.get("cliqueClusterAproxima")),
        ("inclinar liga o relevo 3D", r.get("inclinarLiga3D") == {"terreno": True, "botaoAceso": True}, r.get("inclinarLiga3D")),
        ("elevação real na Prefeitura (800–900 m)", isinstance(r.get("elevacaoPrefeitura_m"), (int, float)) and 800 <= r["elevacaoPrefeitura_m"] <= 900, r.get("elevacaoPrefeitura_m")),
        ("sem exceção no roteiro", "excecao" not in r, r.get("excecao", "")[:200]),
    ]


def main() -> int:
    # Console do Windows (cp1252) não imprime alguns símbolos; força UTF-8.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if not MAP_FILE.exists():
        sys.exit("Mapa não encontrado. Rode antes: python main.py --no-browser")
    folder = Path(tempfile.mkdtemp(prefix="geosbs_site_"))
    shutil.copy(MAP_FILE, folder / "geosbs.html")
    shutil.copy(HARNESS, folder / "harness.html")
    httpd, port = serve(folder)
    try:
        print(f"Servindo em http://localhost:{port} — executando o roteiro (~2 min)...")
        result = run_browser(f"http://localhost:{port}/harness.html")
    finally:
        httpd.shutdown()
        shutil.rmtree(folder, ignore_errors=True)
    rows = checks(result)
    for name, ok, value in rows:
        print(f"  {'OK  ' if ok else 'FALHA'}  {name:44} {value}")
    print(f"Satélite em uso: {result.get('fonteSatelite')}")
    failed = sum(not ok for _, ok, _ in rows)
    print(f"\n{len(rows) - failed}/{len(rows)} verificações passaram.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
