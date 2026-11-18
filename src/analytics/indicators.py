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
import shapely

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


SIGNIFICANCE = 0.05  # nível de significância do teste de Clark-Evans


def clark_evans(points: gpd.GeoDataFrame, area_km2: float,
                perimeter_km: float | None = None) -> dict | None:
    """Índice do vizinho mais próximo de Clark & Evans (1954).

    R = distância média observada ao vizinho mais próximo / distância esperada
    numa distribuição aleatória (0,5 / sqrt(n/A)).
    R < 1 indica agrupamento; R ≈ 1, aleatoriedade; R > 1, dispersão.

    Significância: z = (observada - esperada) / SE, com p-valor bicaudal pela
    distribuição normal. O padrão só é declarado agrupado/disperso se p < 0,05;
    caso contrário, "não significativo" (não dá para descartar o acaso).

    Efeito de borda: perto do limite falta vizinho do lado de fora, o que infla as
    distâncias e, com poucos pontos, faz pontos aleatórios parecerem "dispersos".
    Com `perimeter_km`, aplica a correção de Donnelly (1978):
        esperada = 0,5·sqrt(A/n) + (0,0514 + 0,041/sqrt(n))·P/n
        SE       = sqrt(0,0703·A/n² + 0,037·P·sqrt(A/n⁵))
    Sem perímetro, usa as fórmulas originais (0,5/sqrt(n/A) e 0,26136/sqrt(n²/A)).
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
    if perimeter_km:
        per_m = perimeter_km * 1000
        expected = 0.5 * math.sqrt(area_m2 / n) + (0.0514 + 0.041 / math.sqrt(n)) * per_m / n
        se = math.sqrt(0.0703 * area_m2 / n ** 2 + 0.037 * per_m * math.sqrt(area_m2 / n ** 5))
    else:
        expected = 0.5 / math.sqrt(n / area_m2)
        se = 0.26136 / math.sqrt(n * n / area_m2)
    r = observed / expected
    z = (observed - expected) / se
    p_value = math.erfc(abs(z) / math.sqrt(2))
    if p_value < SIGNIFICANCE:
        pattern = "agrupado" if r < 1 else "disperso"
    else:
        pattern = "não significativo"
    return {"n": n, "dist_media_obs_m": round(observed, 1),
            "dist_media_esperada_m": round(expected, 1), "R": round(r, 3),
            "z": round(z, 2), "p_valor": round(p_value, 4), "padrao": pattern}


def _mean_nn(coords: np.ndarray) -> float:
    diff = coords[:, None, :] - coords[None, :, :]
    dist = np.sqrt((diff ** 2).sum(axis=2))
    np.fill_diagonal(dist, np.inf)
    return float(dist.min(axis=1).mean())


def _random_points(region, n: int, rng: np.random.Generator) -> np.ndarray:
    """n pontos uniformes dentro de `region` (amostragem por rejeição no retângulo envolvente)."""
    minx, miny, maxx, maxy = region.bounds
    out = np.empty((0, 2))
    while len(out) < n:
        cand = np.column_stack([rng.uniform(minx, maxx, 4 * n), rng.uniform(miny, maxy, 4 * n)])
        out = np.vstack([out, cand[shapely.contains_xy(region, cand[:, 0], cand[:, 1])]])
    return out[:n]


def clark_evans_monte_carlo(points: gpd.GeoDataFrame, region, n_sim: int = 999,
                            seed: int = 42) -> dict | None:
    """Clark-Evans com teste de Monte Carlo (Besag & Diggle, 1977).

    A distância esperada é a média de `n_sim` sorteios de n pontos aleatórios
    DENTRO da própria área de estudo (`region`, em metros), o que incorpora o
    efeito de borda e o formato irregular dos bairros, em que as fórmulas
    analíticas (inclusive a correção de Donnelly, feita para áreas compactas)
    falham. p-valor bicaudal pela posição do valor observado entre os sorteios.
    Semente fixa: o resultado é reprodutível.
    """
    n = len(points)
    if n < 3:
        return None
    metric = points.to_crs(settings.CRS_METRIC)
    observed = _mean_nn(np.column_stack([metric.geometry.x, metric.geometry.y]))
    rng = np.random.default_rng(seed)
    sims = np.array([_mean_nn(_random_points(region, n, rng)) for _ in range(n_sim)])
    expected = float(sims.mean())
    low = (1 + (sims <= observed).sum()) / (n_sim + 1)
    high = (1 + (sims >= observed).sum()) / (n_sim + 1)
    p_value = min(1.0, 2 * min(low, high))
    r = observed / expected
    if p_value < SIGNIFICANCE:
        pattern = "agrupado" if r < 1 else "disperso"
    else:
        pattern = "não significativo"
    return {"n": n, "dist_media_obs_m": round(observed, 1), "dist_media_esperada_m": round(expected, 1),
            "R": round(r, 3), "p_valor": round(p_value, 3), "padrao": pattern}


def spatial_patterns(pois: gpd.GeoDataFrame, bairros: gpd.GeoDataFrame,
                     n_sim: int = 999) -> pd.DataFrame:
    """Clark-Evans por categoria (Monte Carlo), só com pontos dentro da área dos bairros."""
    est = establishments(pois)
    inside = est[est["bairro"] != FORA_DE_BAIRRO]
    study = bairros.to_crs(settings.CRS_METRIC).geometry.union_all()   # área de estudo: bairros
    rows = []
    for cat in load_categories():
        res = clark_evans_monte_carlo(inside[inside["categoria"] == cat.id], study, n_sim=n_sim)
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
        "bairro_maior_quantidade": _pick(top_count, "total", table),
        "bairro_menor_quantidade": _pick(low_count, "total", table),
        "bairro_maior_densidade": _pick(top_density, "densidade_km2", table),
        "bairro_menor_densidade": _pick(low_density, "densidade_km2", table),
        "data_coleta": data_coleta,
    }


def regions(pois: gpd.GeoDataFrame, municipio: gpd.GeoDataFrame, table: gpd.GeoDataFrame) -> dict:
    """Quantidade e densidade em duas regiões: área dos bairros × resto do município.

    Os bairros do IBGE cobrem só a área urbana; o resto do município (área rural e
    lacunas da malha) não tem bairro oficial. Tratar esse resto como uma região
    própria evita que os registros dali fiquem "soltos" nas análises. A região NÃO
    entra no ranking de bairros, porque não é um bairro.
    """
    est = establishments(pois)
    labels = {c.id: c.label for c in load_categories()}
    mun_km2 = float(municipio.to_crs(settings.CRS_METRIC).area.sum()) / 1e6
    urb_km2 = float(table["area_km2"].sum())
    fora = est["bairro"] == FORA_DE_BAIRRO
    rows = []
    for nome, area, n in (("Área urbana (bairros do IBGE)", urb_km2, int((~fora).sum())),
                          ("Fora dos bairros (área rural e lacunas)", mun_km2 - urb_km2, int(fora.sum()))):
        rows.append({"regiao": nome, "area_km2": round(area, 1), "total": n,
                     "densidade_km2": round(n / area, 2) if area else 0.0,
                     "pct_area": round(100 * area / mun_km2, 1),
                     "pct_registros": round(100 * n / len(est), 1) if len(est) else 0.0})
    fora_cat = est[fora]["categoria"].map(labels).value_counts()
    return {"tabela": rows, "fora_por_categoria": {k: int(v) for k, v in fora_cat.items()}}


def _pick(row: pd.Series | None, field: str, table: gpd.GeoDataFrame | None = None) -> dict | None:
    """Bairro com o valor extremo; `empatados` lista todos os bairros com o mesmo valor."""
    if row is None:
        return None
    value = float(row[field]) if "dens" in field else int(row[field])
    out = {"bairro": row["NM_BAIRRO"], "valor": value}
    if table is not None:
        tied = table.loc[np.isclose(table[field].astype(float), float(row[field])), "NM_BAIRRO"].tolist()
        if len(tied) > 1:
            out["empatados"] = tied
    return out
