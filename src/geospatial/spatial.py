"""Operações espaciais: reprojeção, área e atribuição de bairro."""
from __future__ import annotations

import geopandas as gpd

from config import settings

FORA_DE_BAIRRO = "Fora dos bairros oficiais"


def add_area_km2(polygons: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Calcula a área em km² numa projeção métrica (UTM 22S).

    Calcular área em graus (CRS geográfico) daria um valor sem significado.
    """
    out = polygons.copy()
    out["area_km2"] = polygons.to_crs(settings.CRS_METRIC).area / 1_000_000
    return out


def assign_bairro(points: gpd.GeoDataFrame, bairros: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Atribui a cada ponto o bairro que o contém (junção espacial ponto-em-polígono).

    Usa-se a geometria, e não o campo de endereço digitado, porque o campo
    textual costuma ser ausente ou inconsistente. Pontos que não caem em
    nenhum bairro (ex.: zona rural) recebem FORA_DE_BAIRRO.
    """
    bairros_web = bairros.to_crs(points.crs)[["CD_BAIRRO", "NM_BAIRRO", "geometry"]]
    joined = gpd.sjoin(points, bairros_web, how="left", predicate="within")
    joined = joined[~joined.index.duplicated(keep="first")]
    joined["bairro"] = joined["NM_BAIRRO"].fillna(FORA_DE_BAIRRO)
    joined["cd_bairro"] = joined["CD_BAIRRO"]
    return joined.drop(columns=["index_right", "NM_BAIRRO", "CD_BAIRRO"])
