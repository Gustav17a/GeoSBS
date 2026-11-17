import geopandas as gpd
import pandas as pd
import pytest

from src.analytics import indicators
from src.data_collection.categories import classify
from src.data_collection.osm import build_query
from src.data_processing.deduplicate import name_similarity, remove_duplicates
from src.data_processing.normalize import build_address, osm_to_dataframe
from src.data_processing.validate import validate
from src.geospatial.spatial import FORA_DE_BAIRRO, add_area_km2, assign_bairro


def _processed(overpass_file, municipio, bairros):
    df = osm_to_dataframe(overpass_file)
    pois, rejected, stats = validate(df, municipio)
    pois, dups = remove_duplicates(pois)
    return assign_bairro(pois, bairros), rejected, stats, dups


@pytest.mark.parametrize("tags,expected", [
    ({"amenity": "pharmacy"}, "farmacias"),
    ({"healthcare": "pharmacy", "amenity": "pharmacy"}, "farmacias"),
    ({"amenity": "clinic"}, "saude"),
    ({"amenity": "school"}, "educacao"),
    ({"amenity": "police"}, "seguranca"),
    ({"highway": "bus_stop"}, "transporte"),
    ({"amenity": "townhall"}, "servicos_publicos"),
    ({"leisure": "park"}, "lazer"),
    ({"tourism": "museum"}, "outros"),
])
def test_classify(tags, expected):
    assert classify(tags)[0] == expected


def test_classify_unknown():
    assert classify({"shop": "bakery"}) is None


def test_query_contains_bbox_and_keys():
    q = build_query((-26.4, -49.5, -26.1, -49.1))
    assert "[out:json]" in q and "out center tags;" in q
    assert '"amenity"~' in q and "(-26.40000,-49.50000,-26.10000,-49.10000)" in q


def test_build_address():
    assert build_address({"addr:street": "Rua A", "addr:housenumber": "5"}) == "Rua A, 5"
    assert build_address({}) is None


def test_normalize_discards_unclassified(overpass_file):
    df = osm_to_dataframe(overpass_file)
    assert "osm:node/6" not in set(df["id"])
    assert len(df) == 6
    way = df[df["id"] == "osm:way/2"].iloc[0]
    assert way["lat"] == -26.2551  # usa o 'center' de vias


def test_validate_rejects_outside_and_invalid(overpass_file, municipio):
    df = osm_to_dataframe(overpass_file)
    df.loc[len(df)] = {**df.iloc[0].to_dict(), "id": "osm:node/99", "lat": None}
    pois, rejected, stats = validate(df, municipio)
    assert stats["fora_do_municipio"] == 1
    assert stats["coordenada_invalida"] == 1
    assert set(rejected["motivo_rejeicao"]) == {"fora_do_municipio", "coordenada_invalida"}
    assert "sem_nome" in pois.loc[pois["id"] == "osm:node/7", "flags"].iloc[0]


def test_name_similarity():
    assert name_similarity("E.E.B. São José", "EEB Sao Jose") > 0.85
    assert name_similarity("Escola A", None) == 0.0


def test_deduplicate_keeps_most_complete(overpass_file, municipio):
    pois, _, _ = validate(osm_to_dataframe(overpass_file), municipio)
    cleaned, dups = remove_duplicates(pois)
    assert len(dups) == 1
    assert dups.iloc[0]["id_mantido"] == "osm:node/1"  # tem endereço
    assert "osm:way/2" not in set(cleaned["id"])


def test_unnamed_points_are_not_merged(municipio):
    df = pd.DataFrame([
        {"id": f"osm:node/{i}", "nome": None, "categoria": "transporte", "subcategoria": "highway=bus_stop",
         "endereco": None, "lat": -26.25, "lon": -49.39 + i * 1e-5, "fonte": "OpenStreetMap",
         "id_fonte": f"node/{i}", "tipo_geometria": "node", "data_coleta": None, "flags": ""}
        for i in range(2)])
    pois, _, _ = validate(df, municipio)
    cleaned, dups = remove_duplicates(pois)
    assert len(cleaned) == 2 and dups.empty


def test_assign_bairro(overpass_file, municipio, bairros):
    pois, *_ = _processed(overpass_file, municipio, bairros)
    lookup = dict(zip(pois["id"], pois["bairro"]))
    assert lookup["osm:node/1"] == "Oeste"
    assert lookup["osm:node/3"] == "Leste"


def test_area_is_metric(bairros):
    areas = add_area_km2(bairros)["area_km2"]
    # 0,01° x 0,01° a ~26° S ≈ 1,11 km x 1,0 km ≈ 1,1 km²
    assert 0.9 < areas.iloc[0] < 1.3


def test_indicators_by_bairro_and_summary(overpass_file, municipio, bairros):
    pois, *_ = _processed(overpass_file, municipio, bairros)
    table = indicators.by_bairro(pois, bairros)
    row = table.set_index("NM_BAIRRO")
    assert row.loc["Oeste", "educacao"] == 1
    assert row.loc["Leste", "total"] == 2          # farmácia + clínica (parada de ônibus não conta)
    assert row.loc["Vazio", "total"] == 0          # bairro sem dados aparece como zero, não inventado
    s = indicators.summary(pois, table)
    assert s["total_estabelecimentos"] == 3
    assert s["paradas_onibus"] == 1
    assert s["bairros_sem_registros"] == ["Vazio"]
    assert s["bairro_maior_quantidade"]["bairro"] == "Leste"


def test_proximity_distances(overpass_file, municipio, bairros):
    pois, *_ = _processed(overpass_file, municipio, bairros)
    prox = indicators.proximity(pois, bairros).set_index("NM_BAIRRO")
    assert prox.loc["Leste", "dist_farmacias_m"] < prox.loc["Oeste", "dist_farmacias_m"]


def test_clark_evans_detects_clustering():
    import numpy as np
    rng = np.random.default_rng(0)
    xs = -49.39 + rng.normal(0, 0.0003, 30)
    ys = -26.25 + rng.normal(0, 0.0003, 30)
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(xs, ys), crs="EPSG:4326")
    res = indicators.clark_evans(pts, area_km2=4.0)
    assert res["R"] < 1 and res["padrao"] == "agrupado"


def test_points_outside_bairros(municipio, bairros):
    pts = gpd.GeoDataFrame({"id": ["a"]}, geometry=gpd.points_from_xy([-49.0], [-26.0]), crs="EPSG:4326")
    assert assign_bairro(pts, bairros)["bairro"].iloc[0] == FORA_DE_BAIRRO


def test_build_map_smoke(tmp_path, overpass_file, municipio, bairros):
    from src.visualization.map_builder import HEAT_LAYER, build_map
    pois, *_ = _processed(overpass_file, municipio, bairros)
    table = indicators.by_bairro(pois, bairros)
    out = build_map(pois, municipio, table, indicators.summary(pois, table), tmp_path / "m.html")
    html = out.read_text(encoding="utf-8")
    assert "geosbs-panel" in html and HEAT_LAYER in html
    assert ("Educação (1)" in html or "Educa\\u00e7\\u00e3o (1)" in html) and "Escola A" in html
