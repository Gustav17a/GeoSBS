"""Identificação de registros duplicados.

No OSM, um mesmo estabelecimento às vezes aparece duas vezes: como ponto
(nó) e como área (via), ou cadastrado por mapeadores diferentes. Considera-se
duplicata o par que:
  - pertence à mesma categoria;
  - está a até DEDUP_MAX_DISTANCE_M metros;
  - tem nomes iguais ou muito parecidos (similaridade >= DEDUP_MIN_NAME_SIMILARITY).
Registros sem nome nunca são unidos por este critério, pois não há como
confirmar que são o mesmo lugar (ex.: duas paradas de ônibus vizinhas).

Ao escolher qual registro manter, prefere-se o mais completo
(com endereço) e, em empate, o polígono (via/relação), que costuma
representar o terreno inteiro.
"""
from __future__ import annotations

import unicodedata
from difflib import SequenceMatcher

import geopandas as gpd
import pandas as pd

from config import settings

_GEOM_PRIORITY = {"way": 0, "relation": 1, "node": 2}
DUP_COLUMNS = ["id_mantido", "id_removido", "nome_mantido", "nome_removido",
               "categoria", "distancia_m", "similaridade"]


def normalize_name(name: str | None) -> str:
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", name.lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return " ".join(text.replace("-", " ").replace(".", " ").split())


def name_similarity(a: str | None, b: str | None) -> float:
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb).ratio()


def _score(r: pd.Series) -> tuple[int, int]:
    return (0 if pd.notna(r["endereco"]) else 1, _GEOM_PRIORITY.get(r["tipo_geometria"], 3))


def find_duplicates(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Retorna os pares de prováveis duplicatas, com o registro a manter."""
    metric = gdf.to_crs(settings.CRS_METRIC).reset_index(drop=True)
    named = metric[metric["nome"].notna()]
    if len(named) < 2:
        return pd.DataFrame(columns=DUP_COLUMNS)

    # Junção espacial ponto x buffer: encontra todos os vizinhos próximos.
    buffers = named[["geometry"]].copy()
    buffers["geometry"] = named.buffer(settings.DEDUP_MAX_DISTANCE_M)
    joined = gpd.sjoin(named[["geometry"]], buffers, predicate="within")
    right_col = "index_right"

    records = []
    for idx_a, idx_b in zip(joined.index, joined[right_col]):
        if idx_a >= idx_b:
            continue
        a, b = metric.loc[idx_a], metric.loc[idx_b]
        if a["categoria"] != b["categoria"]:
            continue
        sim = name_similarity(a["nome"], b["nome"])
        if sim < settings.DEDUP_MIN_NAME_SIMILARITY:
            continue
        keep, drop = (a, b) if _score(a) <= _score(b) else (b, a)
        records.append({
            "id_mantido": keep["id"], "id_removido": drop["id"],
            "nome_mantido": keep["nome"], "nome_removido": drop["nome"],
            "categoria": a["categoria"],
            "distancia_m": round(a.geometry.distance(b.geometry), 1),
            "similaridade": round(sim, 3),
        })
    return pd.DataFrame(records, columns=DUP_COLUMNS)


def remove_duplicates(gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """Remove duplicatas e devolve (dados_limpos, relatório_de_pares_removidos).

    Em cadeias (A~B e B~C), um registro já removido não é usado como
    referência para remover outro, evitando apagar todos os membros do grupo.
    """
    pairs = find_duplicates(gdf)
    dropped: set[str] = set()
    applied = []
    for row in pairs.itertuples(index=False):
        if row.id_mantido in dropped or row.id_removido in dropped:
            continue
        dropped.add(row.id_removido)
        applied.append(row._asdict())
    cleaned = gdf[~gdf["id"].isin(dropped)].reset_index(drop=True)
    return cleaned, pd.DataFrame(applied, columns=DUP_COLUMNS)
