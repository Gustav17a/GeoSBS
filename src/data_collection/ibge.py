"""Coleta das malhas territoriais oficiais do IBGE.

- Malha Municipal 2025 (limite de São Bento do Sul)
- Malha de Bairros do Censo Demográfico 2022
- População residente do Censo 2022 por bairro e por município

Os arquivos .zip de Santa Catarina são baixados uma vez para data/shapefiles/
e lidos diretamente pelo GeoPandas (via pyogrio), sem precisar descompactar.
"""
from __future__ import annotations

import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd

from config import settings
from src.data_collection.http import download_file

log = logging.getLogger(__name__)


def _zip_path(url: str) -> Path:
    return settings.SHAPEFILES_DIR / url.rsplit("/", 1)[-1]


def _read_filtered(zip_file: Path, code: str) -> gpd.GeoDataFrame:
    gdf = gpd.read_file(f"zip://{zip_file.as_posix()}")
    gdf["CD_MUN"] = gdf["CD_MUN"].astype(str)
    selected = gdf[gdf["CD_MUN"] == code].copy()
    if selected.crs is None:
        selected = selected.set_crs(settings.CRS_IBGE)
    return selected


def load_municipio(force_download: bool = False) -> gpd.GeoDataFrame:
    """Retorna o polígono do município (CRS original do IBGE: SIRGAS 2000)."""
    zip_file = download_file(
        settings.IBGE_MUNICIPIOS_URL, _zip_path(settings.IBGE_MUNICIPIOS_URL), force_download
    )
    gdf = _read_filtered(zip_file, settings.MUNICIPIO_CODIGO_IBGE)
    if gdf.empty:
        raise ValueError(
            f"Código {settings.MUNICIPIO_CODIGO_IBGE} não encontrado em {zip_file.name}."
        )
    return gdf[["CD_MUN", "NM_MUN", "AREA_KM2", "geometry"]]


def load_bairros(force_download: bool = False) -> gpd.GeoDataFrame:
    """Retorna os bairros do município conforme a malha do Censo 2022.

    Observação metodológica: o IBGE representa os bairros por agregação de
    setores censitários, portanto os limites podem diferir levemente da lei
    municipal. Áreas rurais podem ficar fora de qualquer bairro.
    """
    zip_file = download_file(
        settings.IBGE_BAIRROS_URL, _zip_path(settings.IBGE_BAIRROS_URL), force_download
    )
    gdf = _read_filtered(zip_file, settings.MUNICIPIO_CODIGO_IBGE)
    if gdf.empty:
        log.warning("Nenhum bairro encontrado para o município na malha do IBGE.")
    gdf["CD_BAIRRO"] = gdf["CD_BAIRRO"].astype(str)
    return gdf[["CD_BAIRRO", "NM_BAIRRO", "geometry"]].reset_index(drop=True)


def _read_agregado(url: str, key: str, force_download: bool) -> pd.DataFrame:
    zip_file = download_file(url, _zip_path(url), force_download)
    df = pd.read_csv(zip_file, sep=";", encoding="latin-1", dtype=str)
    df = df[df["CD_MUN"] == settings.MUNICIPIO_CODIGO_IBGE]
    df = df[[key, "v0001"]].rename(columns={"v0001": "populacao"})
    df["populacao"] = pd.to_numeric(df["populacao"], errors="coerce")
    return df


def load_populacao(force_download: bool = False) -> tuple[pd.DataFrame, int | None]:
    """População residente do Censo 2022: tabela por bairro e total do município.

    A ligação com a malha de bairros é feita pelo código (CD_BAIRRO), não pelo
    nome, para não depender de acentos ou grafias diferentes.
    """
    bairros = _read_agregado(settings.IBGE_POP_BAIRROS_URL, "CD_BAIRRO", force_download)
    municipio = _read_agregado(settings.IBGE_POP_MUNICIPIOS_URL, "CD_MUN", force_download)
    total = int(municipio["populacao"].iloc[0]) if len(municipio) else None
    if bairros.empty:
        log.warning("População por bairro não encontrada nos agregados do IBGE.")
    return bairros.reset_index(drop=True), total
