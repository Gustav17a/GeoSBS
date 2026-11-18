"""Indicadores e análises espaciais calculados a partir da base processada.

Três conceitos são mantidos separados de propósito:
- QUANTIDADE: número de registros num bairro.
- DENSIDADE: registros por km² do bairro (normaliza pelo tamanho da área).
- POR HABITANTE: registros por 10 mil moradores (Censo 2022; normaliza pela
  população). Não mede atendimento: um hospital no Centro atende a cidade toda.
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


def by_bairro(pois: gpd.GeoDataFrame, bairros: gpd.GeoDataFrame,
              populacao: pd.DataFrame | None = None) -> gpd.GeoDataFrame:
    """Tabela por bairro com contagens por categoria, total, densidade e, se houver
    população (colunas CD_BAIRRO e populacao), registros por 10 mil habitantes."""
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
    if populacao is not None:
        table = table.merge(populacao[["CD_BAIRRO", "populacao"]], on="CD_BAIRRO", how="left")
        pop = table["populacao"]
        table["por_10mil_hab"] = (settings.PER_CAPITA_BASE * table["total"] / pop.where(pop > 0)).round(1)
        table["taxa_instavel"] = pop.lt(settings.POP_MIN_TAXA).fillna(False)
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
    per_capita = {}
    if "por_10mil_hab" in table:
        # Destaques só entre bairros com população suficiente para uma taxa estável.
        stable = table[~table["taxa_instavel"] & table["por_10mil_hab"].notna()]
        per_capita = {
            "bairro_maior_por_hab": _pick(stable.sort_values("por_10mil_hab", ascending=False).iloc[0],
                                          "por_10mil_hab", stable) if len(stable) else None,
            "bairro_menor_por_hab": _pick(stable.sort_values("por_10mil_hab").iloc[0],
                                          "por_10mil_hab", stable) if len(stable) else None,
            "bairros_taxa_instavel": table.loc[table["taxa_instavel"], "NM_BAIRRO"].tolist(),
        }

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
        **per_capita,
        "data_coleta": data_coleta,
    }


def regions(pois: gpd.GeoDataFrame, municipio: gpd.GeoDataFrame, table: gpd.GeoDataFrame,
            pop_municipio: int | None = None) -> dict:
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
    has_pop = pop_municipio is not None and "populacao" in table
    pop_urb = int(table["populacao"].sum()) if has_pop else None
    pops = (pop_urb, pop_municipio - pop_urb) if has_pop else (None, None)
    rows = []
    for (nome, area, n), pop in zip((("Área urbana (bairros do IBGE)", urb_km2, int((~fora).sum())),
                                     ("Fora dos bairros (área rural e lacunas)", mun_km2 - urb_km2, int(fora.sum()))),
                                    pops):
        row = {"regiao": nome, "area_km2": round(area, 1), "total": n,
               "densidade_km2": round(n / area, 2) if area else 0.0,
               "pct_area": round(100 * area / mun_km2, 1),
               "pct_registros": round(100 * n / len(est), 1) if len(est) else 0.0}
        if has_pop:
            row["populacao"] = pop
            row["por_10mil_hab"] = round(settings.PER_CAPITA_BASE * n / pop, 1) if pop else None
        rows.append(row)
    fora_cat = est[fora]["categoria"].map(labels).value_counts()
    out = {"tabela": rows, "fora_por_categoria": {k: int(v) for k, v in fora_cat.items()}}
    if has_pop:
        out["populacao_municipio"] = int(pop_municipio)
        out["por_10mil_hab_municipio"] = round(settings.PER_CAPITA_BASE * len(est) / pop_municipio, 1)
    return out


def _pick(row: pd.Series | None, field: str, table: gpd.GeoDataFrame | None = None) -> dict | None:
    """Bairro com o valor extremo; `empatados` lista todos os bairros com o mesmo valor."""
    if row is None:
        return None
    value = int(row[field]) if field == "total" else float(row[field])
    out = {"bairro": row["NM_BAIRRO"], "valor": value}
    if table is not None:
        tied = table.loc[np.isclose(table[field].astype(float), float(row[field])), "NM_BAIRRO"].tolist()
        if len(tied) > 1:
            out["empatados"] = tied
    return out


_GENERIC_WORDS = {
    "a", "ao", "da", "das", "de", "do", "dos", "e", "em", "na", "no", "o",
    "posto", "unidade", "basica", "saude", "estrategia", "familia", "programa", "centro",
    "atendimento", "atencao", "clinica", "medica", "hospital", "vila", "doutor", "doutora",
    "dr", "dra", "sus", "esf", "ubs", "psf", "municipal", "sao", "bento", "sul",
}


def _name_tokens(name) -> set[str]:
    """Palavras próprias de um nome (sem acento, sem palavras genéricas da saúde)."""
    import re
    import unicodedata
    if not isinstance(name, str):
        return set()
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    text = text.replace("º", "").replace("ª", "")
    return {w for w in re.findall(r"[a-z0-9]+", text) if w not in _GENERIC_WORDS}


def match_cnes_to_osm(units: gpd.GeoDataFrame, saude: gpd.GeoDataFrame) -> pd.DataFrame:
    """Para cada unidade do CNES, procura o registro de saúde correspondente no OSM.

    Regra (conferida nos pares reais de São Bento do Sul):
    - registro do OSM COM nome: corresponde se os nomes têm ao menos uma palavra
      própria em comum (ex.: "1 de Maio", "Central", "UPA") e a distância é de até
      settings.CNES_NAME_MATCH_M; só a distância não basta, porque unidades
      diferentes dividem o mesmo prédio (ex.: CEO e Posto Central);
    - registro do OSM SEM nome: corresponde se está a até settings.CNES_MATCH_M e a
      unidade é de atenção básica (no OSM, postos sem nome são o caso comum).
    """
    metric = settings.CRS_METRIC
    u = units.to_crs(metric)
    s = saude.to_crs(metric).reset_index(drop=True)
    s_tokens = [_name_tokens(n) for n in s["nome"]]
    s_named = [isinstance(n, str) and n.strip() != "" for n in s["nome"]]
    rows = []
    for geom, nome, grupo in zip(u.geometry, u["nome"], u["grupo"]):
        dists = s.distance(geom) if len(s) else pd.Series(dtype=float)
        tokens = _name_tokens(nome)
        best = None
        for i in dists.sort_values().index:
            d = float(dists[i])
            if d > settings.CNES_NAME_MATCH_M:
                break
            if s_named[i] and tokens & s_tokens[i]:
                best = (s.loc[i, "nome"], d, "nome e distância"); break
            if (not s_named[i] and d <= settings.CNES_MATCH_M
                    and grupo == settings.CNES_GRUPO_BASICA):
                best = ("(registro sem nome)", d, "distância"); break
        nearest = (float(dists.min()) if len(dists) else np.nan)
        rows.append({"osm_correspondente": best[0] if best else None,
                     "dist_osm_m": round(best[1]) if best else None,
                     "criterio": best[2] if best else None,
                     "dist_saude_osm_mais_proxima_m": round(nearest) if nearest == nearest else None,
                     "no_osm": best is not None})
    return pd.DataFrame(rows, index=units.index)


def cnes_completeness(units: gpd.GeoDataFrame, pois: gpd.GeoDataFrame,
                      table: gpd.GeoDataFrame) -> tuple[dict, pd.DataFrame]:
    """Compara as unidades públicas de saúde do CNES com os registros de saúde do OSM.

    O CNES NÃO entra nas contagens: serve para medir o quanto o OSM cobre a rede
    pública. Consultórios odontológicos do OSM ficam fora da comparação, porque
    não são unidades da rede pública. Retorna o resumo (JSON) e a tabela por
    unidade (CSV).
    """
    if units is None or units.empty:
        return {}, pd.DataFrame()
    saude = pois[(pois["categoria"] == "saude") & (pois["subcategoria"] != "amenity=dentist")]
    u = units.copy()
    u = u.join(match_cnes_to_osm(u, saude))

    basica = u[u["grupo"] == settings.CNES_GRUPO_BASICA]
    est = establishments(pois)
    rows = []
    for nome in [*table["NM_BAIRRO"], FORA_DE_BAIRRO]:
        nu, ns = u[u["bairro"] == nome], est[(est["bairro"] == nome) & (est["categoria"] == "saude")]
        rows.append({"bairro": nome, "cnes_unidades": int(len(nu)),
                     "cnes_atencao_basica": int((nu["grupo"] == settings.CNES_GRUPO_BASICA).sum()),
                     "cnes_no_osm": int(nu["no_osm"].sum()),
                     "osm_saude": int(len(ns)),
                     "osm_estabelecimentos": int((est["bairro"] == nome).sum())})
    by_bairro = pd.DataFrame(rows)
    vazios = by_bairro[(by_bairro["osm_estabelecimentos"] == 0) & (by_bairro["cnes_unidades"] > 0)
                       & (by_bairro["bairro"] != FORA_DE_BAIRRO)]
    grupos = {}
    for g, sub in u.groupby("grupo"):
        grupos[g] = {"cnes": int(len(sub)), "no_osm": int(sub["no_osm"].sum())}
    summary = {
        "unidades": int(len(u)),
        "unidades_no_osm": int(u["no_osm"].sum()),
        "por_grupo": grupos,
        "atencao_basica": int(len(basica)),
        "atencao_basica_no_osm": int(basica["no_osm"].sum()),
        "regra": {"distancia_nome_m": settings.CNES_NAME_MATCH_M, "distancia_sem_nome_m": settings.CNES_MATCH_M},
        "bairros_sem_osm_com_cnes": vazios["bairro"].tolist(),
        "por_bairro": by_bairro.to_dict("records"),
        "cadastro": dict(units.attrs),
    }
    detail = pd.DataFrame(u.drop(columns="geometry"))[
        ["cnes", "nome", "grupo", "bairro", "bairro_cnes", "endereco", "atende_sus", "atualizado_em",
         "lat", "lon", "no_osm", "osm_correspondente", "dist_osm_m", "criterio",
         "dist_saude_osm_mais_proxima_m"]]
    return summary, detail.sort_values(["grupo", "bairro", "nome"]).reset_index(drop=True)
