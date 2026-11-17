"""Indicadores e análises espaciais calculados a partir da base processada.

Três conceitos são mantidos separados de propósito:
- QUANTIDADE: número de registros num bairro.
- DENSIDADE: registros por km² do bairro (normaliza pelo tamanho da área).
- PROXIMIDADE: distância de um ponto do bairro até a unidade mais próxima,
  uma aproximação simples de acessibilidade geográfica (em linha reta,
  sem considerar ruas, relevo ou capacidade de atendimento).
"""
from __future__ import annotations

import math

import geopandas as gpd
import numpy as np
import pandas as pd

from config import settings
from src.data_collection.categories import load_categories
from src.geospatial.spatial import FORA_DE_BAIRRO, add_area_km2


def establishments(pois: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Filtra os registros que contam como estabelecimentos/equipamentos."""
    return pois[~pois["subcategoria"].isin(settings.NOT_ESTABLISHMENT_SUBCATEGORIES)]


def by_bairro(pois: gpd.GeoDataFrame, bairros: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Tabela por bairro com contagens por categoria, total e densidade."""
    est = establishments(pois)
    cat_ids = [c.id for c in load_categories()]
    counts = (
        est[est["bairro"] != FORA_DE_BAIRRO]
        .pivot_table(index="bairro", columns="categoria", values="id",
                     aggfunc="count", fill_value=0)
        .reindex(columns=cat_ids, fill_value=0)
    )
    table = add_area_km2(bairros)[["CD_BAIRRO", "NM_BAIRRO", "area_km2", "geometry"]]
    table = table.merge(counts, left_on="NM_BAIRRO", right_index=True, how="left")
    table[cat_ids] = table[cat_ids].fillna(0).astype(int)
    table["total"] = table[cat_ids].sum(axis=1)
    table["densidade_km2"] = (table["total"] / table["area_km2"]).round(2)
    total_all = table["total"].sum()
    table["participacao_pct"] = (100 * table["total"] / total_all).round(1) if total_all else 0.0
    table["area_km2"] = table["area_km2"].round(3)
    return table.sort_values("total", ascending=False).reset_index(drop=True)


def proximity(pois: gpd.GeoDataFrame, bairros: gpd.GeoDataFrame) -> pd.DataFrame:
    """Distância (m) do ponto representativo de cada bairro à unidade mais próxima.

    Usa `representative_point()` (garantidamente dentro do polígono) em vez do
    centróide, que pode cair fora de bairros com formato irregular.
    """
    ref = bairros.to_crs(settings.CRS_METRIC)[["NM_BAIRRO", "geometry"]].copy()
    ref["geometry"] = ref.representative_point()
    result = ref[["NM_BAIRRO"]].copy()
    metric = pois.to_crs(settings.CRS_METRIC)
    for cat in settings.PROXIMITY_CATEGORIES:
        subset = metric[metric["categoria"] == cat][["geometry"]]
        if subset.empty:
            result[f"dist_{cat}_m"] = np.nan
            continue
        nearest = gpd.sjoin_nearest(ref, subset, distance_col="dist")
        nearest = nearest[~nearest.index.duplicated()]
        result[f"dist_{cat}_m"] = nearest["dist"].round(0)
    return result.reset_index(drop=True)


def clark_evans(points: gpd.GeoDataFrame, area_km2: float) -> dict | None:
    """Índice do vizinho mais próximo de Clark & Evans (1954).

    R = distância média observada ao vizinho mais próximo / distância esperada
    numa distribuição aleatória (0,5 / sqrt(n/A)).
    R < 1 indica agrupamento; R ≈ 1, aleatoriedade; R > 1, dispersão.
    Não há correção de efeito de borda; interpretar como indicativo.
    """
    n = len(points)
    if n < 3 or area_km2 <= 0:
        return None
    metric = points.to_crs(settings.CRS_METRIC).reset_index(drop=True)
    coords = np.column_stack([metric.geometry.x, metric.geometry.y])
    diff = coords[:, None, :] - coords[None, :, :]
    dist = np.sqrt((diff ** 2).sum(axis=2))
    np.fill_diagonal(dist, np.inf)
    observed = dist.min(axis=1).mean()
    area_m2 = area_km2 * 1_000_000
    expected = 0.5 / math.sqrt(n / area_m2)
    r = observed / expected
    pattern = "agrupado" if r < 0.9 else ("disperso" if r > 1.1 else "próximo do aleatório")
    return {"n": n, "dist_media_obs_m": round(observed, 1),
            "dist_media_esperada_m": round(expected, 1), "R": round(r, 3), "padrao": pattern}


def spatial_patterns(pois: gpd.GeoDataFrame, bairros: gpd.GeoDataFrame) -> pd.DataFrame:
    """Clark-Evans por categoria, considerando só pontos dentro da área dos bairros."""
    est = establishments(pois)
    inside = est[est["bairro"] != FORA_DE_BAIRRO]
    area = add_area_km2(bairros)["area_km2"].sum()
    rows = []
    for cat in load_categories():
        res = clark_evans(inside[inside["categoria"] == cat.id], area)
        if res:
            rows.append({"categoria": cat.label, **res})
    return pd.DataFrame(rows)


def summary(pois: gpd.GeoDataFrame, table: gpd.GeoDataFrame) -> dict:
    """Indicadores gerais do painel, todos derivados da base."""
    est = establishments(pois)
    labels = {c.id: c.label for c in load_categories()}
    per_cat = est["categoria"].value_counts().reindex(list(labels), fill_value=0)
    with_data = table[table["total"] > 0]
    top_count = table.iloc[0] if len(table) else None
    low_count = table.sort_values(["total", "densidade_km2"]).iloc[0] if len(table) else None
    top_density = table.sort_values("densidade_km2", ascending=False).iloc[0] if len(table) else None
    low_density = table.sort_values("densidade_km2").iloc[0] if len(table) else None
    data_coleta = pois["data_coleta"].max() if len(pois) else None

    return {
        "total_estabelecimentos": int(len(est)),
        "total_registros_mapa": int(len(pois)),
        "paradas_onibus": int(len(pois) - len(est)),
        "por_categoria": {labels[k]: int(v) for k, v in per_cat.items()},
        "categoria_mais_registros": labels[per_cat.idxmax()] if per_cat.sum() else None,
        "bairros_analisados": int(len(table)),
        "bairros_com_registros": int(len(with_data)),
        "bairros_sem_registros": table.loc[table["total"] == 0, "NM_BAIRRO"].tolist(),
        "fora_dos_bairros": int((est["bairro"] == FORA_DE_BAIRRO).sum()),
        "bairro_maior_quantidade": _pick(top_count, "total"),
        "bairro_menor_quantidade": _pick(low_count, "total"),
        "bairro_maior_densidade": _pick(top_density, "densidade_km2"),
        "bairro_menor_densidade": _pick(low_density, "densidade_km2"),
        "data_coleta": data_coleta,
    }


def _pick(row: pd.Series | None, field: str) -> dict | None:
    if row is None:
        return None
    return {"bairro": row["NM_BAIRRO"], "valor": float(row[field]) if "dens" in field else int(row[field])}
