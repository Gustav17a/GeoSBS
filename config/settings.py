"""Configurações centrais do GeoSBS.

Todos os caminhos são construídos com pathlib para funcionar igualmente
no Windows, Linux e macOS.
"""
import os
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
# Bairros: Censo 2022 é a malha de bairros mais recente publicada pelo IBGE.
_GEOFTP = "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais"
# Malha Municipal 2025: versão mais recente do limite oficial. Em relação à de 2022,
# o IBGE revisou a divisa com Campo Alegre (área oficial 495,772 -> 495,001 km²).
IBGE_MUNICIPIOS_URL = (
    f"{_GEOFTP}/malhas_municipais/municipio_2025/UFs/SC/SC_Municipios_2025.zip"
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

# --- Satélite de alta resolução (Esri World Imagery) ---------------------------
# Chave de API da ArcGIS Location Platform (conta gratuita: 2 milhões de tiles/mês).
# Defina a variável de ambiente GEOSBS_ESRI_KEY ou crie o arquivo .env na raiz do
# projeto com a linha GEOSBS_ESRI_KEY=... (o .env está no .gitignore).
# Num site estático a chave fica visível no HTML: restrinja os domínios permitidos
# (ex.: gustav17a.github.io e localhost) no painel da Esri.
# Sem chave, o mapa usa o Sentinel-2 (10 m), de licença aberta.
def _env_file_value(name: str) -> str:
    env = ROOT_DIR / ".env"
    if not env.exists():
        return ""
    for line in env.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == name:
            return value.strip().strip('"').strip("'")
    return ""


ESRI_API_KEY = os.environ.get("GEOSBS_ESRI_KEY", "").strip() or _env_file_value("GEOSBS_ESRI_KEY")
# Data de vencimento da chave (AAAA-MM-DD), informada no painel da Esri ao criá-la.
# Não é secreta; serve para o aviso de vencimento em main.py.
ESRI_KEY_EXPIRES = (os.environ.get("GEOSBS_ESRI_KEY_EXPIRA", "").strip()
                    or _env_file_value("GEOSBS_ESRI_KEY_EXPIRA"))
ESRI_KEY_WARN_DAYS = 30

# Margem (fração do tamanho do município) que o usuário pode navegar além do limite.
MAP_NAV_MARGIN = 0.35
