"""Dados SINTÉTICOS usados apenas nos testes automatizados.

Não representam São Bento do Sul: são geometrias simples (quadrados) e
pontos inventados para verificar a lógica do código de forma controlada.
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture
def municipio():
    # Quadrado de ~0,02° (~2 km) de lado.
    return gpd.GeoDataFrame({"CD_MUN": ["0000000"], "NM_MUN": ["Teste"], "AREA_KM2": ["4"]},
                            geometry=[box(-49.40, -26.26, -49.38, -26.24)], crs="EPSG:4674")


@pytest.fixture
def bairros():
    return gpd.GeoDataFrame(
        {"CD_BAIRRO": ["1", "2", "3"], "NM_BAIRRO": ["Oeste", "Leste", "Vazio"]},
        geometry=[box(-49.40, -26.26, -49.39, -26.25), box(-49.39, -26.26, -49.38, -26.25),
                  box(-49.40, -26.25, -49.38, -26.24)],
        crs="EPSG:4674",
    )


@pytest.fixture
def overpass_file(tmp_path):
    elements = [
        {"type": "node", "id": 1, "lat": -26.255, "lon": -49.395,
         "tags": {"amenity": "school", "name": "Escola A", "addr:street": "Rua X", "addr:housenumber": "10"}},
        {"type": "way", "id": 2, "center": {"lat": -26.2551, "lon": -49.3951},
         "tags": {"amenity": "school", "name": "Escola  A"}},  # duplicata (via) da Escola A
        {"type": "node", "id": 3, "lat": -26.255, "lon": -49.385,
         "tags": {"amenity": "pharmacy", "name": "Farmácia B"}},
        {"type": "node", "id": 4, "lat": -26.256, "lon": -49.386, "tags": {"highway": "bus_stop"}},
        {"type": "node", "id": 5, "lat": -26.10, "lon": -49.10,
         "tags": {"amenity": "hospital", "name": "Fora"}},  # fora do município
        {"type": "node", "id": 6, "lat": -26.257, "lon": -49.384,
         "tags": {"shop": "bakery", "name": "Sem categoria"}},  # não classificado
        {"type": "node", "id": 7, "lat": -26.2555, "lon": -49.3845,
         "tags": {"amenity": "clinic"}},  # sem nome
    ]
    path = tmp_path / "osm_overpass_test.json"
    path.write_text(json.dumps({"elements": elements, "geosbs_meta": {"coletado_em": "2026-11-17T10:00:00"}}),
                    encoding="utf-8")
    return path
