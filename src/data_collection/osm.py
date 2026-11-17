"""Coleta de pontos de interesse no OpenStreetMap via Overpass API.

Estratégia de uso responsável:
- Uma única consulta por coleta, limitada ao retângulo envolvente do município
  (o recorte exato pelo polígono do IBGE é feito depois, localmente).
- A resposta bruta é salva em data/raw/ com data e hora; execuções seguintes
  reutilizam esse arquivo, a menos que se peça uma nova coleta.
- Em caso de HTTP 429 (limite) ou 504 (servidor ocupado), espera e tenta de
  novo; depois tenta a instância alternativa.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path

import requests

from config import settings
from src.data_collection.categories import load_categories

log = logging.getLogger(__name__)

RAW_PREFIX = "osm_overpass_"


def build_query(bbox: tuple[float, float, float, float]) -> str:
    """Monta a consulta Overpass QL a partir das regras de categorias.

    bbox = (sul, oeste, norte, leste) em graus WGS 84.
    `nwr` busca nós, vias e relações; `out center tags` devolve um ponto
    central para áreas (ex.: o terreno de uma escola).
    """
    keys: dict[str, set[str]] = {}
    for cat in load_categories():
        for key, values in cat.rules.items():
            keys.setdefault(key, set()).update(values)

    s, w, n, e = bbox
    lines = [
        f'  nwr["{key}"~"^({"|".join(sorted(values))})$"]({s:.5f},{w:.5f},{n:.5f},{e:.5f});'
        for key, values in sorted(keys.items())
    ]
    return (
        f"[out:json][timeout:{settings.OVERPASS_TIMEOUT_S}];\n(\n"
        + "\n".join(lines)
        + "\n);\nout center tags;"
    )


def latest_raw_file() -> Path | None:
    files = sorted(settings.RAW_DIR.glob(f"{RAW_PREFIX}*.json"))
    return files[-1] if files else None


def fetch(bbox: tuple[float, float, float, float], force: bool = False) -> Path:
    """Executa a consulta (ou reaproveita o cache) e retorna o caminho do JSON bruto."""
    cached = latest_raw_file()
    if cached and not force:
        log.info("Usando coleta OSM existente: %s", cached.name)
        return cached

    query = build_query(bbox)
    headers = {"User-Agent": settings.HTTP_USER_AGENT}
    errors: list[str] = []

    for endpoint in settings.OVERPASS_ENDPOINTS:
        for attempt in range(1, 4):
            try:
                log.info("Consultando Overpass: %s (tentativa %d)", endpoint, attempt)
                resp = requests.post(
                    endpoint,
                    data={"data": query},
                    headers=headers,
                    timeout=settings.OVERPASS_TIMEOUT_S + 30,
                )
                if resp.status_code in (429, 504):
                    wait = 30 * attempt
                    log.warning("Overpass respondeu %s. Aguardando %ds.", resp.status_code, wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                payload = resp.json()
                return _save_raw(payload, query, endpoint)
            except (requests.RequestException, ValueError) as exc:
                errors.append(f"{endpoint}: {exc}")
                log.warning("Erro na consulta Overpass: %s", exc)
                time.sleep(10)

    raise RuntimeError(
        "Overpass indisponível. Tente mais tarde ou use https://overpass-turbo.eu "
        "com a consulta em data/raw/overpass_query.txt, exportando o resultado "
        f"como JSON bruto para data/raw/{RAW_PREFIX}manual.json.\n" + "\n".join(errors)
    )


def _save_raw(payload: dict, query: str, endpoint: str) -> Path:
    settings.RAW_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    payload.setdefault("geosbs_meta", {})
    payload["geosbs_meta"].update(
        {"coletado_em": datetime.now().isoformat(timespec="seconds"), "endpoint": endpoint}
    )
    path = settings.RAW_DIR / f"{RAW_PREFIX}{stamp}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (settings.RAW_DIR / "overpass_query.txt").write_text(query, encoding="utf-8")
    log.info("Coleta salva em %s (%d elementos)", path.name, len(payload.get("elements", [])))
    return path
