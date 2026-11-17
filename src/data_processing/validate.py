"""Validação de coordenadas e de completude dos registros."""
from __future__ import annotations

import logging

import geopandas as gpd
import pandas as pd

from config import settings

log = logging.getLogger(__name__)


def add_flag(df: pd.DataFrame, mask: pd.Series, flag: str) -> None:
    """Acrescenta `flag` à coluna 'flags' (separadas por ';') nas linhas de `mask`."""
    current = df.loc[mask, "flags"].fillna("")
    df.loc[mask, "flags"] = current.where(current == "", current + ";") + flag


def coordinate_problems(df: pd.DataFrame) -> pd.Series:
    """Máscara de coordenadas ausentes, não numéricas ou fora da faixa válida."""
    lat = pd.to_numeric(df["lat"], errors="coerce")
    lon = pd.to_numeric(df["lon"], errors="coerce")
    return lat.isna() | lon.isna() | ~lat.between(-90, 90) | ~lon.between(-180, 180)


def validate(
    df: pd.DataFrame, municipio: gpd.GeoDataFrame
) -> tuple[gpd.GeoDataFrame, pd.DataFrame, dict]:
    """Separa registros válidos e rejeitados e devolve estatísticas de qualidade.

    Regras:
    1. Coordenada inválida  -> rejeitado ('coordenada_invalida').
    2. Fora do município (com tolerância de BOUNDARY_TOLERANCE_M) -> rejeitado
       ('fora_do_municipio'). Isso remove o excedente do retângulo da consulta.
    3. Nome ausente -> mantido, com flag 'sem_nome'.
    4. Endereço ausente -> mantido, com flag 'sem_endereco'.
    """
    df = df.copy()
    df["flags"] = df["flags"].fillna("")
    stats: dict[str, int] = {"registros_recebidos": len(df)}

    bad_coords = coordinate_problems(df)
    stats["coordenada_invalida"] = int(bad_coords.sum())
    rejected = [df[bad_coords].assign(motivo_rejeicao="coordenada_invalida")]
    df = df[~bad_coords].copy()
    df["lat"] = df["lat"].astype(float)
    df["lon"] = df["lon"].astype(float)

    gdf = gpd.GeoDataFrame(
        df, geometry=gpd.points_from_xy(df["lon"], df["lat"]), crs=settings.CRS_WEB
    )
    limit = (
        municipio.to_crs(settings.CRS_METRIC)
        .buffer(settings.BOUNDARY_TOLERANCE_M)
        .union_all()
    )
    inside = gdf.to_crs(settings.CRS_METRIC).within(limit)
    stats["fora_do_municipio"] = int((~inside).sum())
    rejected.append(
        pd.DataFrame(gdf[~inside].drop(columns="geometry")).assign(
            motivo_rejeicao="fora_do_municipio"
        )
    )
    gdf = gdf[inside].copy()

    add_flag(gdf, gdf["nome"].isna(), "sem_nome")
    add_flag(gdf, gdf["endereco"].isna(), "sem_endereco")
    stats["sem_nome"] = int(gdf["nome"].isna().sum())
    stats["sem_endereco"] = int(gdf["endereco"].isna().sum())

    rejected_df = pd.concat([r for r in rejected if not r.empty], ignore_index=True) \
        if any(not r.empty for r in rejected) else pd.DataFrame()
    return gdf.reset_index(drop=True), rejected_df, stats
