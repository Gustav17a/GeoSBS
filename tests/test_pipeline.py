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


@pytest.mark.parametrize("tags,expected", [
    # Centro comunitário só é serviço público com operador público; senão, "outros".
    ({"amenity": "community_centre", "operator:type": "public"}, "servicos_publicos"),
    ({"amenity": "community_centre"}, "outros"),
    ({"amenity": "community_centre", "community_centre": "events_venue"}, "outros"),
    # Jardim só entra em lazer se tiver nome; sem nome, é descartado.
    ({"leisure": "garden", "name": "Jardim Botânico"}, "lazer"),
    ({"leisure": "garden"}, None),
    ({"leisure": "garden", "name": "  "}, None),
])
def test_classify_conditions(tags, expected):
    result = classify(tags)
    assert (result[0] if result else None) == expected


def test_normalize_counts_discarded(overpass_file):
    df = osm_to_dataframe(overpass_file)
    assert df.attrs["descartados_pelas_regras"] == df.attrs["elementos_osm"] - len(df) == 1


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
    assert res["R"] < 1 and res["padrao"] == "agrupado" and res["p_valor"] < 0.05


def test_clark_evans_regular_grid_is_dispersed():
    """Uma grade regular é o caso clássico de dispersão (R > 1, significativo)."""
    import numpy as np
    g = np.linspace(-49.395, -49.385, 6)
    xs, ys = np.meshgrid(g, np.linspace(-26.255, -26.245, 6))
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(xs.ravel(), ys.ravel()), crs="EPSG:4326")
    res = indicators.clark_evans(pts, area_km2=1.0)
    assert res["R"] > 1 and res["padrao"] == "disperso"


def test_clark_evans_edge_correction_controls_false_positives():
    """Pontos aleatórios: com a correção de Donnelly, ~5% de falsos positivos e R médio ~1."""
    import numpy as np
    from shapely.geometry import box
    area = gpd.GeoSeries([box(-49.40, -26.26, -49.38, -26.24)], crs="EPSG:4326").to_crs("EPSG:31982").iloc[0]
    a_km2, p_km = area.area / 1e6, area.length / 1000
    sig, rs = 0, []
    for seed in range(200):
        rng = np.random.default_rng(seed)
        pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(rng.uniform(-49.40, -49.38, 8),
                                                           rng.uniform(-26.26, -26.24, 8)), crs="EPSG:4326")
        res = indicators.clark_evans(pts, a_km2, perimeter_km=p_km)
        sig += res["p_valor"] < 0.05
        rs.append(res["R"])
    assert sig / 200 < 0.10 and abs(np.mean(rs) - 1) < 0.05


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


def _web_map(tmp_path, overpass_file, municipio, bairros):
    import json
    import re
    from src.visualization.maplibre_builder import build_web_map
    pois, *_ = _processed(overpass_file, municipio, bairros)
    table = indicators.by_bairro(pois, bairros)
    out = build_web_map(pois, municipio, table, indicators.summary(pois, table), tmp_path / "w.html")
    html = out.read_text(encoding="utf-8")
    data = json.loads(re.search(r"const GEO = (\{.*?\});\n", html, flags=re.S).group(1))
    return pois, html, data


def test_web_map_embeds_consistent_data(tmp_path, overpass_file, municipio, bairros):
    pois, html, data = _web_map(tmp_path, overpass_file, municipio, bairros)
    assert "maplibre-gl@" in html and 'id="map"' in html
    # Todo registro do mapa aparece uma única vez: estabelecimentos + paradas.
    assert len(data["pois"]["features"]) + len(data["paradas"]["features"]) == len(pois)
    assert all(f["properties"]["estab"] for f in data["pois"]["features"])
    assert sum(c["count"] for c in data["categories"]) == len(data["pois"]["features"])
    assert {c["id"] for c in data["categories"]} >= {"saude", "educacao", "transporte"}
    assert len(data["bairros"]["features"]) == len(bairros)
    assert data["summary"]["total_estabelecimentos"] == len(data["pois"]["features"])


def test_web_map_rounds_coordinates(tmp_path, overpass_file, municipio, bairros):
    _, _, data = _web_map(tmp_path, overpass_file, municipio, bairros)
    def walk(c):
        if isinstance(c, (int, float)):
            yield c
        else:
            for x in c:
                yield from walk(x)
    coords = [v for f in data["bairros"]["features"] + data["pois"]["features"]
              for v in walk(f["geometry"]["coordinates"])]
    assert coords and all(round(v, 6) == v for v in coords)


def test_lucide_icons_exist_for_all_categories():
    from src.data_collection.categories import load_categories
    from src.visualization.maplibre_builder import ICONS_DIR, lucide_inner_svg
    for c in load_categories():
        assert (ICONS_DIR / f"{c.lucide}.svg").exists(), c.id
        inner = lucide_inner_svg(c.lucide)
        assert "<path" in inner or "<circle" in inner or "<rect" in inner
        assert "<script" not in inner.lower()


def test_web_map_escapes_html_in_names(tmp_path, municipio, bairros):
    """Um nome malicioso no OSM não pode virar código na página."""
    import json
    from src.visualization.maplibre_builder import build_web_map
    df = pd.DataFrame([{"id": "osm:node/1", "nome": "</script><script>alert(1)</script>",
                        "categoria": "saude", "subcategoria": "amenity=clinic", "endereco": None,
                        "lat": -26.255, "lon": -49.395, "fonte": "OpenStreetMap", "id_fonte": "node/1",
                        "tipo_geometria": "node", "data_coleta": "2026-11-17", "flags": ""}])
    pois, _, _ = validate(df, municipio)
    pois = assign_bairro(pois, bairros)
    table = indicators.by_bairro(pois, bairros)
    html = build_web_map(pois, municipio, table, indicators.summary(pois, table),
                         tmp_path / "x.html").read_text(encoding="utf-8")
    assert "</script><script>alert(1)" not in html


def test_web_map_focus_on_municipio(tmp_path, overpass_file, municipio, bairros):
    """O mapa abre no município inteiro e a navegação fica limitada aos arredores."""
    from shapely.geometry import box, shape
    _, html, data = _web_map(tmp_path, overpass_file, municipio, bairros)
    assert "bounds: GEO.bounds.municipio" in html and "maxBounds: GEO.bounds.max" in html
    (mx0, my0), (mx1, my1) = data["bounds"]["municipio"]
    (nx0, ny0), (nx1, ny1) = data["bounds"]["max"]
    assert nx0 < mx0 and ny0 < my0 and nx1 > mx1 and ny1 > my1   # município inteiro dentro dos limites
    mask = shape(data["mask"]["features"][0]["geometry"])
    mun = shape(data["municipio"]["features"][0]["geometry"])
    assert mask.intersection(mun).area < 1e-9 * mun.area          # o véu não cobre o município
    assert mask.union(mun).covers(box(nx0, ny0, nx1, ny1))         # mas cobre o resto da área navegável


def test_web_map_esri_key_only_when_configured(tmp_path, overpass_file, municipio, bairros):
    from src.visualization.maplibre_builder import build_web_map
    pois, *_ = _processed(overpass_file, municipio, bairros)
    table = indicators.by_bairro(pois, bairros)
    summ = indicators.summary(pois, table)
    sem = build_web_map(pois, municipio, table, summ, tmp_path / "a.html", esri_key="").read_text(encoding="utf-8")
    com = build_web_map(pois, municipio, table, summ, tmp_path / "b.html", esri_key="CHAVE-TESTE").read_text(encoding="utf-8")
    assert 'const ESRI_KEY = "";' in sem and "CHAVE-TESTE" not in sem
    assert 'const ESRI_KEY = "CHAVE-TESTE";' in com
    assert "server.arcgisonline.com" not in com   # só o endpoint oficial com chave


def test_env_file_is_ignored_by_git():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    assert ".env" in (root / ".gitignore").read_text(encoding="utf-8").split()


def test_reverse_geocode_offline_uses_only_cache(tmp_path):
    """Sem --reverse-geocode, só o cache é usado: nenhuma requisição ao Nominatim."""
    from src.geospatial.geocoding import Geocoder, fill_missing_addresses
    g = Geocoder(cache_file=tmp_path / "cache.json")
    g.cache["rev|-26.250000,-49.380000"] = "Rua A, 10"
    def boom():
        raise AssertionError("não deveria acessar a internet")
    g._client = boom
    df = pd.DataFrame({"endereco": [None, None, "Rua B, 5"], "lat": [-26.25, -26.26, -26.27],
                       "lon": [-49.38, -49.39, -49.40]})
    out = fill_missing_addresses(df, online=False, geocoder=g)
    assert out.at[0, "endereco"] == "Rua A, 10 (aprox., geocodificação reversa)"
    assert pd.isna(out.at[1, "endereco"]) and out.at[2, "endereco"] == "Rua B, 5"


def test_clark_evans_monte_carlo_on_irregular_area():
    """Monte Carlo: pontos aleatórios numa área em 'L' quase nunca dão padrão; agrupados, sim."""
    import numpy as np
    from shapely.geometry import box
    region = box(0, 0, 3000, 1000).union(box(0, 0, 1000, 3000))        # metros, formato em L
    to_gdf = lambda xy: gpd.GeoDataFrame(geometry=gpd.points_from_xy(xy[:, 0], xy[:, 1]),
                                         crs="EPSG:31982").to_crs("EPSG:4326")
    sig = 0
    for seed in range(40):
        pts = indicators._random_points(region, 8, np.random.default_rng(100 + seed))
        sig += indicators.clark_evans_monte_carlo(to_gdf(pts), region, n_sim=199, seed=seed)["p_valor"] < 0.05
    assert sig <= 6                                                      # ~5% esperado
    clustered = np.column_stack([np.random.default_rng(0).normal(500, 40, 12),
                                 np.random.default_rng(1).normal(500, 40, 12)])
    res = indicators.clark_evans_monte_carlo(to_gdf(clustered), region, n_sim=199)
    assert res["padrao"] == "agrupado" and res["R"] < 0.6


def test_regions_split_urban_and_outside(overpass_file, municipio, bairros):
    """Área urbana + fora dos bairros = município inteiro, e todos os estabelecimentos."""
    pois, *_ = _processed(overpass_file, municipio, bairros)
    table = indicators.by_bairro(pois, bairros)
    reg = indicators.regions(pois, municipio, table)["tabela"]
    est = indicators.establishments(pois)
    mun_km2 = municipio.to_crs("EPSG:31982").area.sum() / 1e6
    assert sum(r["total"] for r in reg) == len(est)
    assert abs(sum(r["area_km2"] for r in reg) - mun_km2) < 0.2
    assert reg[1]["total"] == int((est["bairro"] == FORA_DE_BAIRRO).sum())


def test_esri_key_expiry_warning(monkeypatch):
    from datetime import date
    import main
    from config import settings
    monkeypatch.setattr(settings, "ESRI_API_KEY", "CHAVE")
    monkeypatch.setattr(settings, "ESRI_KEY_EXPIRES", "2027-02-15")
    assert main.check_esri_key(date(2026, 11, 18)) is None                       # longe do vencimento
    assert "vence em 15 dias" in main.check_esri_key(date(2027, 1, 31))
    assert "VENCEU" in main.check_esri_key(date(2027, 2, 16))
    monkeypatch.setattr(settings, "ESRI_API_KEY", "")
    assert "Sem chave" in main.check_esri_key(date(2026, 11, 18))


def test_latest_raw_file_uses_data_date_not_name(tmp_path, monkeypatch):
    """Uma exportação manual ANTIGA não deve vencer uma coleta automática mais nova."""
    import json
    from config import settings
    from src.data_collection import osm
    monkeypatch.setattr(settings, "RAW_DIR", tmp_path)
    w = lambda name, ts: (tmp_path / name).write_text(json.dumps({"osm3s": {"timestamp_osm_base": ts}, "elements": []}))
    w("osm_overpass_20261117_174117.json", "2026-11-17T20:40:18Z")
    w("osm_overpass_manual.json", "2026-10-01T00:00:00Z")
    assert osm.latest_raw_file().name == "osm_overpass_20261117_174117.json"
    w("osm_overpass_manual.json", "2026-12-01T00:00:00Z")                 # manual mais nova vence
    assert osm.latest_raw_file().name == "osm_overpass_manual.json"


def test_summary_lists_ties(overpass_file, municipio, bairros):
    pois, *_ = _processed(overpass_file, municipio, bairros)
    table = indicators.by_bairro(pois, bairros)
    low = indicators.summary(pois, table)["bairro_menor_quantidade"]
    zeros = table.loc[table["total"] == low["valor"], "NM_BAIRRO"].tolist()
    assert len(zeros) < 2 or sorted(low["empatados"]) == sorted(zeros)
