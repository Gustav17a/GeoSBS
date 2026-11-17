"""Conversão da resposta bruta do Overpass para uma tabela padronizada.

Esquema padronizado de cada registro (ponto de interesse):
    id, nome, categoria, subcategoria, endereco, lat, lon,
    fonte, id_fonte, tipo_geometria, data_coleta, flags
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd

from config import settings
from src.data_collection.categories import classify

SCHEMA = [
    "id", "nome", "categoria", "subcategoria", "endereco", "lat", "lon",
    "fonte", "id_fonte", "tipo_geometria", "data_coleta", "flags",
]


def build_address(tags: dict[str, str]) -> str | None:
    street = tags.get("addr:street")
    number = tags.get("addr:housenumber")
    suburb = tags.get("addr:suburb")
    parts = []
    if street:
        parts.append(f"{street}, {number}" if number else street)
    if suburb:
        parts.append(suburb)
    if tags.get("addr:postcode"):
        parts.append(f"CEP {tags['addr:postcode']}")
    return " - ".join(parts) if parts else None


def _element_coords(el: dict) -> tuple[float | None, float | None]:
    if el.get("type") == "node":
        return el.get("lat"), el.get("lon")
    center = el.get("center") or {}
    return center.get("lat"), center.get("lon")


def osm_to_dataframe(raw_file: Path) -> pd.DataFrame:
    """Lê o JSON do Overpass e devolve um DataFrame no esquema padronizado.

    Elementos cujas tags não casam com nenhuma categoria são descartados.
    """
    payload = json.loads(Path(raw_file).read_text(encoding="utf-8"))
    collected = payload.get("geosbs_meta", {}).get("coletado_em") or datetime.fromtimestamp(
        Path(raw_file).stat().st_mtime
    ).isoformat(timespec="seconds")

    rows = []
    elements = payload.get("elements", [])
    for el in elements:
        tags = el.get("tags") or {}
        classified = classify(tags)
        if classified is None:
            continue
        category, subcategory = classified
        lat, lon = _element_coords(el)
        osm_id = f"{el.get('type')}/{el.get('id')}"
        rows.append(
            {
                "id": f"osm:{osm_id}",
                "nome": (tags.get("name") or tags.get("official_name") or "").strip() or None,
                "categoria": category,
                "subcategoria": subcategory,
                "endereco": build_address(tags),
                "lat": lat,
                "lon": lon,
                "fonte": "OpenStreetMap",
                "id_fonte": osm_id,
                "tipo_geometria": el.get("type"),
                "data_coleta": collected,
                "flags": "",
            }
        )
    df = pd.DataFrame(rows, columns=SCHEMA)
    # Rastreabilidade: quantos elementos da coleta foram descartados pelas regras.
    df.attrs["elementos_osm"] = len(elements)
    df.attrs["descartados_pelas_regras"] = len(elements) - len(rows)
    return df


def to_geodataframe(df: pd.DataFrame) -> gpd.GeoDataFrame:
    """Cria geometrias de ponto a partir de lat/lon (WGS 84)."""
    return gpd.GeoDataFrame(
        df.copy(), geometry=gpd.points_from_xy(df["lon"], df["lat"]), crs=settings.CRS_WEB
    )
