"""Unidades de saúde do CNES (Cadastro Nacional de Estabelecimentos de Saúde).

Fonte OFICIAL usada para comparação com o OpenStreetMap: não entra nas contagens
de estabelecimentos (que continuam só com o OSM), aparece numa camada própria e
serve para medir a completude do OSM na saúde.

- Coleta: API de dados abertos do Ministério da Saúde, uma página por vez, com
  pausa entre as páginas; a resposta é guardada em data/raw/ e reaproveitada.
- Filtro: unidades de atendimento da rede pública (UBS/ESF, CAPS, UPA, centros
  especializados municipais) e hospitais que atendem pelo SUS.
- Coordenadas: informadas pelo próprio estabelecimento ao CNES; podem ter erro.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

from config import settings

log = logging.getLogger(__name__)


def cache_file() -> Path:
    return settings.RAW_DIR / f"cnes_{settings.CNES_MUNICIPIO}.json"


def _get_page(page: int, retries: int = 3) -> list[dict]:
    params = {"codigo_municipio": settings.CNES_MUNICIPIO,
              "limit": settings.CNES_PAGE_SIZE, "offset": page}
    headers = {"accept": "application/json", "User-Agent": settings.HTTP_USER_AGENT}
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(settings.CNES_API_URL, params=params, headers=headers, timeout=60)
            resp.raise_for_status()
            return resp.json().get("estabelecimentos", [])
        except (requests.RequestException, ValueError) as exc:
            if attempt == retries:
                raise
            log.warning("CNES: falha na página %d (%s). Nova tentativa.", page, exc)
            time.sleep(5 * attempt)
    return []


def fetch(force: bool = False, max_pages: int = 200) -> Path:
    """Baixa todos os estabelecimentos do município (ou reaproveita o cache)."""
    path = cache_file()
    if path.exists() and not force:
        log.info("Usando cache: %s", path.name)
        return path
    items: list[dict] = []
    for page in range(max_pages):
        rows = _get_page(page)
        items += rows
        if len(rows) < settings.CNES_PAGE_SIZE:
            break
        time.sleep(settings.CNES_PAUSE_S)
    payload = {"fonte": settings.CNES_API_URL, "codigo_municipio": settings.CNES_MUNICIPIO,
               "baixado_em": datetime.now().isoformat(timespec="seconds"),
               "estabelecimentos": items}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("CNES: %d estabelecimentos salvos em %s", len(items), path.name)
    return path


def _is_public_care(row: pd.Series) -> bool:
    """Unidade de atendimento da rede pública ou hospital que atende pelo SUS."""
    tipo = row["codigo_tipo_unidade"]
    if tipo not in settings.CNES_GRUPOS:
        return False
    publica = str(row.get("descricao_natureza_juridica_estabelecimento") or "").startswith("1")
    sus = row.get("estabelecimento_faz_atendimento_ambulatorial_sus") == "SIM"
    hospital = settings.CNES_GRUPOS[tipo] == "Hospital e urgência"
    return publica or (hospital and sus)


_SMALL = {"a", "ao", "da", "de", "do", "das", "dos", "e", "em", "na", "no"}
_ACRONYMS = {"upa", "caps", "ceo", "cem", "cvs", "pics", "cadia", "caic", "cam", "cat", "sus",
             "ubs", "esf", "psf", "tea", "ii"}


def _title(text) -> str | None:
    """Nomes do CNES vêm em MAIÚSCULAS e sem acento; só a caixa é ajustada."""
    if not isinstance(text, str) or not text.strip():
        return None
    words = text.strip().lower().split()
    return " ".join(w.upper() if w in _ACRONYMS else w if (w in _SMALL and i) else w.capitalize()
                    for i, w in enumerate(words))


def load_units(path: Path, municipio: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Unidades públicas com coordenadas dentro do município.

    `attrs` guarda as contagens para o relatório: total do cadastro, unidades
    públicas selecionadas, sem coordenada e fora do limite municipal.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    df = pd.DataFrame(payload["estabelecimentos"])
    attrs = {"cadastro_total": int(len(df)), "baixado_em": payload.get("baixado_em")}
    if df.empty:
        out = gpd.GeoDataFrame(geometry=[], crs=settings.CRS_WEB)
        out.attrs = attrs | {"selecionadas": 0, "sem_coordenada": 0, "cadastro_duplicado": 0,
                             "fora_do_municipio": 0, "no_mapa": 0}
        return out

    df = df[df.apply(_is_public_care, axis=1)].copy()
    selected = len(df)
    lat, lon = "latitude_estabelecimento_decimo_grau", "longitude_estabelecimento_decimo_grau"
    no_coord = df[lat].isna() | df[lon].isna()
    df = df[~no_coord]
    # Um mesmo local pode ter dois cadastros (ex.: a UPA aparece como tipo 2 e 73):
    # fica o de tipo mais específico (maior código).
    before = len(df)
    df = (df.sort_values("codigo_tipo_unidade", ascending=False)
            .drop_duplicates(subset=["nome_fantasia", lat, lon]))
    duplicated = before - len(df)

    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df[lon], df[lat]), crs=settings.CRS_WEB)
    limite = municipio.to_crs(settings.CRS_METRIC).buffer(settings.BOUNDARY_TOLERANCE_M).union_all()
    inside = gdf.to_crs(settings.CRS_METRIC).within(limite)

    numero = df["numero_estabelecimento"].fillna("").astype(str).str.strip()
    out = gpd.GeoDataFrame({
        "cnes": df["codigo_cnes"].astype(int).astype(str).str.zfill(7),
        "codigo_unidade": df["codigo_estabelecimento_saude"].astype(str),
        "nome": df["nome_fantasia"].map(_title),
        "tipo_codigo": df["codigo_tipo_unidade"].astype(int),
        "grupo": df["codigo_tipo_unidade"].map(settings.CNES_GRUPOS),
        "endereco": [", ".join(p for p in (_title(r) or "", n if n not in ("", "S/N", "SN") else "") if p) or None
                     for r, n in zip(df["endereco_estabelecimento"], numero)],
        "bairro_cnes": df["bairro_estabelecimento"].map(_title),
        "atende_sus": df["estabelecimento_faz_atendimento_ambulatorial_sus"].eq("SIM"),
        "atualizado_em": df["data_atualizacao"],
        "lat": df[lat].astype(float).round(6),
        "lon": df[lon].astype(float).round(6),
    }, geometry=gdf.geometry, crs=settings.CRS_WEB)[inside.to_numpy()].reset_index(drop=True)
    out.attrs = attrs | {"selecionadas": int(selected), "sem_coordenada": int(no_coord.sum()),
                         "cadastro_duplicado": int(duplicated),
                         "fora_do_municipio": int((~inside).sum()), "no_mapa": int(len(out))}
    return out
