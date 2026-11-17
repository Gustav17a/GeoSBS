# GeoSBS — Plataforma de Inteligência Geográfica de São Bento do Sul

Aplicação em Python que coleta, valida, integra e analisa dados geográficos de
equipamentos urbanos de **São Bento do Sul (SC)** e gera um **mapa interativo**
(MapLibre GL JS) com mapa vetorial, satélite, relevo sombreado e **terreno em 3D com
elevação real**, painel de indicadores, filtros por categoria, agrupamento de
marcadores, mapa de calor e mapas coropléticos por bairro.

**Mapa publicado:** <https://gustav17a.github.io/GeoSBS/>

> Trabalho acadêmico da disciplina de Geolocalização — Bacharelado em Sistemas de
> Informação, UDESC.

![Mapa GeoSBS](docs/img/geosbs_mapa.png)

![Relevo 3D: a escarpa da Serra do Mar entre Corupá e o planalto de São Bento do Sul](docs/img/geosbs_relevo_3d.png)

## O que o sistema faz

| Etapa | Descrição | Módulo |
|---|---|---|
| Coleta | Malha municipal 2022 e Malha de Bairros do Censo 2022 (IBGE); pontos de interesse do OpenStreetMap (uma consulta Overpass, com cache) | `src/data_collection` |
| Processamento | Esquema padronizado, classificação em 8 categorias, validação de coordenadas, recorte pelo limite municipal, flags de dados ausentes, remoção de duplicatas | `src/data_processing` |
| Geoprocessamento | Reprojeção (SIRGAS 2000 → UTM 22S / WGS 84), áreas em km², junção espacial ponto-em-polígono, geocodificação com Geopy/Nominatim | `src/geospatial` |
| Análise | Quantidade, densidade (por km²) e proximidade por bairro; índice do vizinho mais próximo (Clark-Evans) por categoria | `src/analytics` |
| Visualização | Mapa MapLibre GL JS: mapa vetorial, satélite, híbrido, relevo e 3D; ícones SVG por categoria; clusters com anel de composição; mapa de calor; coropléticos; popups; painel e legenda dinâmica. Versão clássica em Folium/Leaflet como alternativa | `src/visualization` |

Categorias: Saúde · Educação · Farmácias · Segurança pública · Transporte ·
Serviços públicos · Lazer e espaços públicos · Outros pontos de interesse
(regras em `config/categories.json`).

## Instalação no Windows

Pré-requisitos: **Python 3.12 ou 3.13** e **Git**. O QGIS é opcional (validação visual).

```powershell
# 1. Clonar (ou abrir a pasta do projeto)
git clone https://github.com/Gustav17a/GeoSBS.git
cd GeoSBS

# 2. Criar e ativar o ambiente virtual
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
#   Se o PowerShell bloquear scripts, rode uma vez:
#   Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 3. Instalar dependências
python -m pip install --upgrade pip
pip install -r requirements.txt

# 4. Executar
python main.py
```

O mapa é salvo em `output/maps/geosbs.html` e aberto no navegador. A cada execução, a cópia
publicada em `docs/index.html` (GitHub Pages) é atualizada automaticamente.
Também é gerada `geosbs_classico.html` (Folium/Leaflet), para computadores sem WebGL.
O mapa precisa de internet para carregar o mapa-base, o satélite e o relevo.

### Opções

```powershell
python main.py --refresh          # nova coleta no OpenStreetMap
python main.py --refresh-ibge     # baixar novamente as malhas do IBGE
python main.py --reverse-geocode  # preencher endereços ausentes via Nominatim (~1 s por registro)
python main.py --no-browser       # não abrir o navegador
python main.py -v                 # log detalhado
python -m pytest                  # testes automatizados
```

### Problemas comuns

| Sintoma | Causa provável / solução |
|---|---|
| `py` não reconhecido | Use `python` ou reinstale o Python marcando "Add to PATH". |
| `Activate.ps1 cannot be loaded` | Execute `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`. |
| Erro ao instalar `pyogrio`/`geopandas` | Atualize o pip (`python -m pip install -U pip`) e confirme Python 64 bits. |
| `Overpass indisponível` / HTTP 429, 502, 504 | Servidores públicos sobrecarregados. Aguarde e rode de novo, ou use o fallback manual descrito abaixo. |
| Download do IBGE falha | Baixe os .zip indicados em `config/settings.py` e coloque em `data/shapefiles/`. |

**Fallback manual do OSM:** abra <https://overpass-turbo.eu>, cole a consulta de
`data/raw/overpass_query.txt`, execute, use *Exportar → dados brutos (JSON)* e salve
como `data/raw/osm_overpass_manual.json`.

## Dados e saídas

```
data/
  raw/          respostas originais com data/hora (nunca editadas) + consulta Overpass
  shapefiles/   SC_Municipios_2022.zip e SC_bairros_CD2022.zip (IBGE)
  processed/    pois.geojson, pois.csv, bairros.geojson
output/
  maps/         geosbs.html (MapLibre) e geosbs_classico.html (Leaflet)
  reports/      resultados.md, indicadores.json, por_bairro.csv, proximidade.csv,
                duplicatas_removidas.csv, registros_rejeitados.csv
```

Para incluir pontos conferidos em outras fontes (ex.: site da Prefeitura), crie
`data/raw/pontos_manuais.csv` (separador `;`) com as colunas
`nome;categoria;endereco;lat;lon;fonte`. Linhas sem `lat/lon` são geocodificadas
pelo endereço.

## Decisões técnicas

- **CRS:** IBGE em SIRGAS 2000 (EPSG:4674); mapa web em WGS 84 (EPSG:4326);
  áreas e distâncias em **SIRGAS 2000 / UTM 22S (EPSG:31982)**. A área
  calculada do município (495,71 km²) confere com a oficial do IBGE (495,772 km²).
- **Bairro de cada ponto** por junção espacial, não pelo endereço digitado.
- **Quantidade ≠ densidade ≠ proximidade:** são calculadas e exibidas separadamente.
- **Paradas de ônibus** aparecem no mapa, mas não contam como estabelecimentos
  nem entram no mapa de calor (distorceriam a comparação entre bairros).
- **Mapa em MapLibre GL JS (BSD-3):** renderização vetorial e 3D no mesmo mapa, sem chave de
  API. Dados embutidos com coordenadas arredondadas a 6 casas e polígonos simplificados (2 m),
  só para exibição: o HTML caiu de 1,4 MB para ~240 KB.
- **Mapas-base sem chave de API:** OpenFreeMap (estilo Liberty, dados OSM); satélite
  EOxCloudless/Sentinel-2 (10 m, CC BY-NC-SA 4.0, uso acadêmico permitido); opção Esri World
  Imagery para alta resolução; relevo e 3D com Terrain Tiles (SRTM/GMTED2010, USGS) no AWS Open
  Data. O 3D usa só elevação real; edificações em 3D foram desligadas porque o OSM quase não
  tem alturas para a cidade e o estilo inventaria valores.
- **Cores e ícones:** 8 cores categóricas validadas para daltonismo (com 8 categorias nenhuma
  paleta é distinguível só pela cor, por isso cada categoria tem também um ícone Lucide, ISC).
- **Uso responsável de APIs:** uma consulta Overpass por coleta, com cache;
  Nominatim limitado a 1 requisição/s, com cache.

## Limitações

- O OpenStreetMap é colaborativo: a completude varia por área e categoria. O mapa
  mostra a distribuição dos **registros coletados**, não a oferta real de serviços.
- Os bairros do IBGE são aproximados por setores censitários e cobrem só a área
  urbana (≈ 82 km² dos 496 km² do município).
- Proximidade é medida em linha reta a partir de um ponto do bairro; não considera
  ruas, relevo, horários ou capacidade de atendimento.
- Resultados por bairro dependem do recorte territorial (Problema da Unidade de Área Modificável).
- O mapa principal precisa de WebGL e de internet. Sem WebGL, use `geosbs_classico.html`.
- O satélite padrão tem 10 m por pixel (bom para matas e relevo, não para ruas). A opção Esri tem
  alta resolução, mas seus termos de uso remetem ao ecossistema ArcGIS.

## Licenças e atribuição

- Dados do OpenStreetMap © colaboradores do OpenStreetMap, licença ODbL.
- Malhas territoriais © IBGE.
- Mapa-base: [OpenFreeMap](https://openfreemap.org) © OpenMapTiles, dados © OpenStreetMap.
- Satélite: EOxCloudless 2024 by EOX IT Services GmbH (Contains modified Copernicus Sentinel
  data 2024), CC BY-NC-SA 4.0. Opcional: imagens © Esri, Maxar, Earthstar Geographics.
- Elevação: Terrain Tiles (AWS Open Data); SRTM e GMTED2010 cortesia do U.S. Geological Survey.
- Ícones: [Lucide](https://lucide.dev) (ISC) — `src/visualization/icons/`.
- Bibliotecas: MapLibre GL JS (BSD-3), Folium/Leaflet (MIT/BSD-2).
- Código: MIT.
