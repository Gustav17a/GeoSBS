"""Configurações centrais do GeoSBS.

Todos os caminhos são construídos com pathlib para funcionar igualmente
no Windows, Linux e macOS.
"""
from pathlib import Path

# --- Caminhos -----------------------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT_DIR / "config"
DATA_DIR = ROOT_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
SHAPEFILES_DIR = DATA_DIR / "shapefiles"
OUTPUT_DIR = ROOT_DIR / "output"
MAPS_DIR = OUTPUT_DIR / "maps"
REPORTS_DIR = OUTPUT_DIR / "reports"
TEMPLATES_DIR = ROOT_DIR / "src" / "visualization" / "templates"
CATEGORIES_FILE = CONFIG_DIR / "categories.json"

# --- Município ----------------------------------------------------------------
MUNICIPIO_NOME = "São Bento do Sul"
MUNICIPIO_UF = "SC"
MUNICIPIO_CODIGO_IBGE = "4215802"

# --- Sistemas de referência de coordenadas (CRS) -------------------------------
# SIRGAS 2000 geográfico: CRS oficial das malhas do IBGE.
CRS_IBGE = "EPSG:4674"
# WGS 84: CRS usado por OpenStreetMap, Leaflet e Folium.
CRS_WEB = "EPSG:4326"
# SIRGAS 2000 / UTM zona 22S: projeção métrica para áreas e distâncias.
# São Bento do Sul (~49,4° O) está na zona UTM 22 (54° O a 48° O).
CRS_METRIC = "EPSG:31982"

# --- Fontes oficiais IBGE (URLs verificadas em 17/11/2026) --------------------
_GEOFTP = "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais"
IBGE_MUNICIPIOS_URL = (
    f"{_GEOFTP}/malhas_municipais/municipio_2022/UFs/SC/SC_Municipios_2022.zip"
)
IBGE_BAIRROS_URL = (
    f"{_GEOFTP}/malhas_de_setores_censitarios__divisoes_intramunicipais/"
    "censo_2022/bairros/shp/UF/SC_bairros_CD2022.zip"
)

# --- OpenStreetMap / Overpass --------------------------------------------------
# Instâncias públicas, tentadas em ordem. Respeitar a política de uso:
# uma consulta por coleta, sem paralelismo, com cache local.
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
OVERPASS_TIMEOUT_S = 180
HTTP_USER_AGENT = "GeoSBS/1.0 (trabalho academico UDESC - Geolocalizacao)"

# --- Parâmetros de processamento ----------------------------------------------
# Tolerância (m) para aceitar pontos colados ao limite municipal.
BOUNDARY_TOLERANCE_M = 50
# Distância máxima (m) e similaridade mínima de nome para considerar duplicata.
DEDUP_MAX_DISTANCE_M = 75
DEDUP_MIN_NAME_SIMILARITY = 0.85

# Registros exibidos no mapa mas excluídos das contagens de "estabelecimentos"
# e do mapa de calor: paradas de ônibus são equipamentos de infraestrutura
# numerosos e distorceriam a comparação entre bairros.
NOT_ESTABLISHMENT_SUBCATEGORIES = {"highway=bus_stop"}

# Categorias usadas na análise de proximidade (centro do bairro -> unidade mais próxima).
PROXIMITY_CATEGORIES = ["saude", "educacao", "farmacias"]

# --- Mapa ---------------------------------------------------------------------
MAP_OUTPUT_FILE = MAPS_DIR / "geosbs.html"            # mapa principal (MapLibre GL JS)
MAP_CLASSIC_FILE = MAPS_DIR / "geosbs_classico.html"  # versão Leaflet/Folium (alternativa sem WebGL)
# Cópia publicada no GitHub Pages (pasta docs/). Atualizada a cada execução.
PAGES_DIR = ROOT_DIR / "docs"
