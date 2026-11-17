# GeoSBS — Plataforma de Inteligência Geográfica de São Bento do Sul

**Disciplina:** Geolocalização · **Curso:** Bacharelado em Sistemas de Informação · **Instituição:** UDESC
**Autor:** Gustavo N. Becker · **Data:** novembro de 2026

> Os números da seção 11 vêm de `output/reports/resultados.md`, gerado automaticamente
> pelo sistema. Ao executar uma nova coleta, atualize-os a partir desse arquivo.

---

## 1. Título

GeoSBS — Plataforma de Inteligência Geográfica de São Bento do Sul: coleta, integração e
análise espacial de equipamentos urbanos com Python e dados abertos.

## 2. Introdução

Saber *onde* estão os serviços de uma cidade é tão importante quanto saber *quantos* existem.
Os Sistemas de Informação Geográfica (SIG) permitem armazenar, relacionar e analisar dados que
têm uma componente de localização. Assim, uma lista de endereços passa a ser informação sobre
o território.

O GeoSBS aplica esses conceitos a São Bento do Sul (SC), município de 495,772 km² e 83.277
habitantes (IBGE, Censo 2022). O sistema integra dados oficiais do IBGE (limite municipal e
bairros) a dados colaborativos do OpenStreetMap (estabelecimentos e equipamentos urbanos). Ele
valida e padroniza os registros, atribui cada ponto a um bairro por operação espacial e gera um
mapa interativo com indicadores calculados automaticamente.

## 3. Justificativa

Informações sobre a distribuição de serviços costumam estar espalhadas em cadastros diferentes,
sem representação espacial integrada. Um mapa analítico ajuda cidadãos, gestores e
pesquisadores a responder perguntas como "quais bairros concentram serviços?" ou "qual a
distância até a unidade de saúde mais próxima?". Do ponto de vista acadêmico, o projeto exercita
todo o ciclo do geoprocessamento: aquisição, tratamento, análise e comunicação cartográfica.

## 4. Problema de pesquisa

Como os serviços e equipamentos urbanos registrados em bases abertas estão distribuídos pelo
território de São Bento do Sul? Que diferenças de quantidade, densidade e proximidade existem
entre os bairros?

## 5. Objetivo geral

Desenvolver uma aplicação em Python que colete, trate, analise e visualize dados geográficos de
equipamentos urbanos de São Bento do Sul, produzindo um mapa interativo e indicadores
reprodutíveis.

## 6. Objetivos específicos

1. Obter as malhas oficiais do município e dos bairros (IBGE) e os pontos de interesse do
   OpenStreetMap.
2. Padronizar, classificar, validar e remover duplicidades dos registros, registrando a origem
   de cada dado.
3. Atribuir os pontos aos bairros por junção espacial e calcular quantidade, densidade e
   proximidade.
4. Identificar padrões de distribuição espacial com o índice do vizinho mais próximo.
5. Produzir um mapa interativo com camadas, agrupamento de marcadores, mapa de calor, mapas
   coropléticos, legenda e painel de indicadores.

## 7. Fundamentação teórica

**Sistemas de Informação Geográfica e geoprocessamento.** Geoprocessamento é o conjunto de
técnicas computacionais que tratam a informação geográfica. Os SIG são as ferramentas que
permitem integrar, armazenar e analisar dados espaciais e seus atributos (CÂMARA; DAVIS;
MONTEIRO, 2001; LONGLEY et al., 2015). Os dados são representados como vetores (pontos,
linhas e polígonos) ou matrizes (*raster*). O GeoSBS usa vetores: pontos para os
estabelecimentos e polígonos para o município e os bairros.

**Georreferenciamento, coordenadas e sistemas de referência.** Uma posição só tem sentido
associada a um sistema de referência. O Brasil adota o SIRGAS 2000, sistema das malhas do IBGE
(EPSG:4674). Serviços web como o OpenStreetMap usam o WGS 84 (EPSG:4326). Coordenadas
geográficas (graus) são inadequadas para medir áreas e distâncias, por isso o projeto reprojeta
os dados para a projeção UTM, zona 22 Sul (EPSG:31982), que é métrica e cobre a região.

**Geocodificação.** Geocodificação é a conversão de descrições textuais de localização, como
endereços, em coordenadas. A geocodificação reversa faz o caminho inverso (GOLDBERG; WILSON;
KNOBLOCK, 2007). O projeto usa a biblioteca Geopy com o serviço Nominatim, respeitando o limite
de uma requisição por segundo.

**Informação geográfica voluntária (VGI).** O OpenStreetMap é um exemplo de VGI, isto é, dados
produzidos por cidadãos que atuam como "sensores" (GOODCHILD, 2007). Estudos de qualidade
mostram que sua precisão pode ser boa, mas a completude varia entre regiões (HAKLAY, 2010).
Isso exige cautela ao interpretar áreas com poucos registros.

**Visualização de dados espaciais.** Mapas coropléticos representam valores agregados por área
com cores graduadas e devem usar taxas ou densidades, e não apenas totais, para não favorecer
áreas grandes (SLOCUM et al., 2009). Mapas de calor estimam a intensidade de ocorrência de
pontos. O agrupamento de marcadores (*clustering*) evita a sobreposição visual em escalas
pequenas.

**Análise de padrões de pontos.** O índice de Clark e Evans (1954) compara a distância média
observada ao vizinho mais próximo com a esperada numa distribuição aleatória. Valores menores
que 1 indicam agrupamento. A primeira lei da Geografia, segundo a qual coisas próximas são mais
relacionadas que as distantes (TOBLER, 1970), fundamenta esse tipo de análise. Resultados
agregados por áreas dependem do recorte adotado, o Problema da Unidade de Área Modificável
(OPENSHAW, 1984).

## 8. Metodologia

| Etapa | Procedimento |
|---|---|
| Aquisição | Download da Malha Municipal 2022 e da Malha de Bairros do Censo 2022 (IBGE, *shapefile*); consulta única à Overpass API do OSM pelo retângulo envolvente do município, salva com data e hora em `data/raw/`. |
| Classificação | Regras de tags OSM → 8 categorias (`config/categories.json`), com condições opcionais por regra (ex.: centro comunitário só é serviço público com operador público); elementos que não casam são descartados e contados no relatório de qualidade. |
| Validação | Coordenadas ausentes ou fora da faixa → rejeitadas; pontos fora do polígono municipal (tolerância de 50 m) → rejeitados; nome/endereço ausentes → mantidos com sinalização. |
| Deduplicação | Mesma categoria, distância ≤ 75 m e similaridade de nome ≥ 0,85; mantém-se o registro mais completo. |
| Análise espacial | Junção ponto-em-polígono para atribuir bairro; área em km² na projeção UTM 22S; densidade = registros/km²; proximidade = distância em linha reta do ponto representativo do bairro à unidade mais próxima; índice de Clark-Evans por categoria. |
| Visualização | Folium (Leaflet) com LayerControl, MarkerCluster, HeatMap, coropléticos e painel HTML/CSS/JS. |
| Verificação | 31 testes automatizados (pytest); conferência da área calculada com a oficial; inspeção visual do mapa. |

Paradas de ônibus são exibidas no mapa, mas excluídas das contagens de estabelecimentos e do
mapa de calor, para não distorcer a comparação entre bairros.

## 9. Tecnologias utilizadas

Python 3.13; Pandas e NumPy (dados tabulares); GeoPandas, Shapely, PyProj e Pyogrio (dados
espaciais, geometria, projeções, leitura de *shapefile*); Folium/Leaflet (mapa web); Geopy
(geocodificação); Requests (HTTP); Jinja2, HTML, CSS e JavaScript (painel); pytest (testes);
QGIS 3.44 (conferência visual); Git/GitHub (versionamento).

## 10. Desenvolvimento do sistema

Arquitetura em pipeline, com módulos de responsabilidade única:

```
coleta (IBGE, OSM) → data/raw → padronização/validação/deduplicação → data/processed
   → junção espacial e indicadores → output/reports → mapa Folium → output/maps/geosbs.html
```

- `src/data_collection`: downloads com cache e novas tentativas; consulta Overpass gerada a
  partir das regras de categoria.
- `src/data_processing`: esquema padronizado (id, nome, categoria, subcategoria, endereço,
  lat, lon, fonte, id_fonte, data_coleta, flags), validação e deduplicação.
- `src/geospatial`: reprojeção, áreas, junção espacial e geocodificação.
- `src/analytics`: indicadores, proximidade, padrões espaciais e relatórios.
- `src/visualization`: mapa e painel.

Decisões relevantes: atribuir o bairro pela geometria, e não pelo endereço digitado; usar
`representative_point()` em vez do centróide (que pode cair fora de polígonos irregulares);
usar quantis nas classes dos coropléticos; cache de todas as respostas externas, para
respeitar as políticas de uso das APIs públicas.

## 11. Resultados obtidos

**Verificações com dados reais (IBGE):**
- A malha de bairros do Censo 2022 contém **20 bairros** para São Bento do Sul.
- A área do município calculada na projeção UTM 22S é **495,71 km²**, contra 495,772 km²
  oficiais (diferença de 0,01%), o que confirma a escolha da projeção.
- Os 20 bairros somam **82,1 km²** (cerca de 17% do município). O restante é área rural, sem
  bairro oficial, e os pontos ali são contabilizados como "fora dos bairros oficiais".

**Coleta e qualidade dos dados (OSM, coleta de 17/11/2026 17:41):**

| Etapa | Registros |
|---|---|
| Elementos recebidos da Overpass API (retângulo envolvente) | 235 |
| Descartados pelas regras de classificação (jardins sem nome) | 17 |
| Rejeitados por estarem fora do município | 45 |
| Rejeitados por coordenada inválida | 0 |
| Duplicatas removidas | 1 |
| **Registros finais no mapa** | **172** |
| ↳ sem nome no OSM (mantidos e sinalizados) | 72 |
| ↳ sem endereço no OSM (mantidos e sinalizados) | 132 |

Quase todos os 45 rejeitados ficam nos municípios vizinhos de Campo Alegre e Corupá, que
caem dentro do retângulo da consulta mas fora do polígono do IBGE. A única duplicata removida
foi o Terminal Urbano do Centenário, mapeado como ponto e como área a 5,9 m de distância.

**Conferência da localização:** nos 31 registros cujo endereço no OSM traz o nome do bairro,
o bairro digitado coincide com o bairro atribuído pela junção espacial em **31 de 31** casos.
Cinco pontos de categorias diferentes foram comparados com o Google Maps: Prefeitura (17 m de
diferença), Fórum (8 m), Corpo de Bombeiros de Oxford (2 m), Hospital e Maternidade Sagrada
Família (54 m) e Univille (74 m). As diferenças maiores ocorrem em objetos que o OSM representa
como áreas (o sistema usa o centro do polígono, o Google usa um ponto de entrada).

**Indicadores gerais:**
- **126 estabelecimentos e equipamentos**, mais 46 paradas de ônibus que aparecem no mapa mas
  não entram nas contagens.
- Por categoria: Lazer e espaços públicos 34 · Educação 26 · Outros pontos de interesse 19 ·
  Serviços públicos 17 · Saúde 14 · Farmácias 7 · Transporte 5 · Segurança pública 4.
  **Categoria com mais registros: Lazer e espaços públicos** (inclui 9 *playgrounds* sem nome).
- 16 dos 20 bairros têm ao menos um registro; **11 registros** ficam fora dos bairros oficiais
  (área rural ou lacunas da malha — por exemplo, o campus do Instituto Federal Catarinense).

**Quantidade e densidade por bairro** (`output/reports/por_bairro.csv`):

| | Bairro | Valor |
|---|---|---|
| Maior quantidade | Centro | 44 registros (38,3% dos que estão em bairros) |
| 2ª maior quantidade | Oxford | 15 registros |
| Maior densidade | Centro | 14,78 por km² |
| 2ª maior densidade | Oxford | 5,66 por km² |
| Menor quantidade e densidade | Industrial Sudoeste, Dona Francisca, Alpino e Rio Vermelho Povoado (empate) | 0 registros |
| Menor densidade entre bairros com registros | Bela Aliança | 0,22 por km² (1 registro) |

Serra Alta é um bom exemplo da diferença entre as medidas: é o **3º em quantidade** (11
registros), mas, por ser o maior bairro (12,06 km²), tem densidade de apenas **0,91 por km²**,
abaixo de bairros com menos registros, como Centenário (1,88), Colonial (1,61) e Boehmerwald (1,37).

**Proximidade** — distância em linha reta (m) do ponto representativo de cada bairro até a
unidade mais próxima (`output/reports/proximidade.csv`):

| Bairro | Saúde | Educação | Farmácia |
|---|---:|---:|---:|
| Centro | 246 | 84 | 116 |
| Schramm | 230 | 1.308 | 1.213 |
| Boehmerwald | 568 | 578 | 1.657 |
| Progresso | 924 | 1.288 | 1.786 |
| Rio Negro | 1.004 | 1.265 | 1.607 |
| Vinte e Cinco de Julho | 1.101 | 649 | 1.085 |
| Colonial | 1.341 | 1.086 | 1.870 |
| Cruzeiro | 1.518 | 335 | 1.247 |
| Oxford | 1.577 | 751 | 769 |
| Industrial Sudoeste | 1.698 | 2.663 | 3.365 |
| Serra Alta | 2.582 | 509 | 603 |
| Brasília | 2.675 | 218 | 2.323 |
| Mato Preto | 2.931 | 487 | 2.159 |
| Dona Francisca | 3.210 | 2.438 | 3.658 |
| Centenário | 3.834 | 1.560 | 3.102 |
| Rio Vermelho - Estação | 4.036 | 4.020 | 5.121 |
| Alpino | 4.146 | 1.849 | 4.326 |
| Bela Aliança | 4.155 | 1.457 | 4.257 |
| Lençol | 4.657 | 1.769 | 6.073 |
| Rio Vermelho Povoado | 5.481 | 4.083 | 5.537 |

O Centro tem as menores distâncias nas três categorias. As maiores distâncias até saúde e
educação estão em Rio Vermelho Povoado (5,5 km e 4,1 km) e até farmácia, em Lençol (6,1 km).
Proximidade não acompanha quantidade: Centenário tem 8 registros, mas está a 3,8 km da unidade
de saúde registrada mais próxima; Schramm tem só 4 registros, mas está a 230 m de uma.

**Padrão espacial — índice do vizinho mais próximo de Clark-Evans** (pontos dentro dos
bairros; por isso *n* pode ser menor que o total da categoria):

| Categoria | n | Dist. média observada (m) | Dist. esperada se aleatório (m) | R | Leitura |
|---|---:|---:|---:|---:|---|
| Serviços públicos | 16 | 425,6 | 1.132,7 | 0,38 | agrupado |
| Farmácias | 7 | 934,2 | 1.712,5 | 0,55 | agrupado |
| Outros pontos de interesse | 10 | 881,2 | 1.432,7 | 0,62 | agrupado |
| Saúde | 14 | 786,8 | 1.210,9 | 0,65 | agrupado |
| Lazer e espaços públicos | 34 | 574,3 | 777,0 | 0,74 | agrupado |
| Educação | 25 | 681,0 | 906,2 | 0,75 | agrupado |
| Segurança pública | 4 | 1.841,5 | 2.265,4 | 0,81 | agrupado |
| Transporte | 5 | 1.946,6 | 2.026,2 | 0,96 | próximo do aleatório |

Interpretação: em sete das oito categorias R < 1, o que indica tendência de agrupamento,
coerente com a concentração de registros no Centro. O resultado deve ser lido com cautela:
(1) não foi feito teste de significância estatística; (2) categorias com poucos pontos
(Segurança, n = 4; Transporte, n = 5; Farmácias, n = 7) produzem valores instáveis, e o
resultado é sensível às regras de classificação — ao tirar 5 centros comunitários de Serviços
públicos, o R dessa categoria passou de 0,61 para 0,38;
(3) não há correção de efeito de borda; e (4) o índice mede o padrão **dos registros do OSM**,
que também reflete onde os mapeadores atuaram mais.

**Leitura dos resultados:** quantidade responde "onde há mais registros" (Centro, Oxford,
Serra Alta); densidade responde "onde eles estão mais concentrados por km²" e favorece bairros
pequenos e centrais (Centro, Oxford); proximidade responde "a que distância fica a unidade mais
próxima" e pode ser boa mesmo em bairros com poucos registros, desde que haja uma unidade perto
do limite do bairro.

## 12. Limitações encontradas

- **Completude do OSM:** o mapa reflete o que foi mapeado. Ausência de registros não significa
  ausência de serviço.
- **Bairros do IBGE:** são aproximados por setores censitários e cobrem só a área urbana; podem
  diferir dos limites da lei municipal. Não foi encontrado *shapefile* oficial da Prefeitura.
- **Proximidade em linha reta:** não considera ruas, relevo (relevante em São Bento do Sul),
  horários ou capacidade de atendimento.
- **MAUP e efeito de borda:** resultados dependem do recorte por bairros; o índice de
  Clark-Evans não tem correção de borda nem teste de significância.
- **Atributos incompletos no OSM:** 72 dos 172 registros (42%) não têm nome e 132 (77%) não têm
  endereço. Eles são mantidos, porque a localização é válida, mas sinalizados.
- **Precisão do limite municipal:** a Malha Municipal do IBGE é compatível com a escala
  1:250.000, então o traçado do limite pode ter erros da ordem de 100 m. Dois registros foram
  rejeitados a 97 m e 139 m do limite (Salão da Capela e Escola Isolada Ernesto Rucker) e podem
  pertencer ao município; a tolerância de 50 m foi mantida para não aceitar pontos de vizinhos.
- **Lacunas na malha de bairros:** alguns equipamentos urbanos ficam fora dos polígonos de
  bairro do IBGE (ex.: campus do Instituto Federal Catarinense) e entram em "fora dos bairros".
- **Classificação por tags:** a categoria depende da tag escolhida pelo mapeador. Duas regras
  foram refinadas após inspeção dos dados reais: `amenity=community_centre` só conta como
  Serviço público quando o OSM indica operador público (`operator:type=public`; caso do Centro
  Comunitário Santinor da Silva) — os demais (casas de eventos, sociedades, associações) vão para
  Outros pontos de interesse; e `leisure=garden` só conta como Lazer quando tem nome, porque os
  jardins sem nome não tinham nenhuma outra tag e podem ser canteiros. Permanecem limitações:
  `amenity=dentist` (Saúde) inclui consultórios particulares, e o registro "Compre Mais"
  (`amenity=marketplace`) não pôde ser confirmado em outra fonte.
- **Empates:** quatro bairros têm zero registros; o relatório automático cita apenas um deles
  como "menor quantidade" e "menor densidade".
- **Disponibilidade de APIs:** durante o desenvolvimento, as instâncias públicas do Overpass
  retornaram erros 502/504 em vários momentos. O sistema trata isso com novas tentativas,
  instâncias alternativas, cache e uma opção de importação manual.

## 13. Conclusão

O GeoSBS mostra que é possível construir, só com dados abertos e bibliotecas livres, uma
plataforma reprodutível de análise espacial municipal. O projeto aplica, de forma integrada,
os conceitos da disciplina: SIG, sistemas de referência, *shapefiles*, geocodificação,
marcadores, agrupamento, camadas, mapas de calor e coropléticos. O principal aprendizado
metodológico é que os dados espaciais exigem validação explícita e interpretação cuidadosa.
Distinguir quantidade, densidade e proximidade e declarar as limitações das fontes é o que
transforma um mapa em informação confiável. Trabalhos futuros: integrar o CNES (saúde) e o
Catálogo de Escolas do INEP, usar a população por setor censitário para calcular indicadores
per capita e medir a acessibilidade pela rede viária.

## 14. Referências

CÂMARA, G.; DAVIS, C.; MONTEIRO, A. M. V. (org.). *Introdução à ciência da geoinformação*.
São José dos Campos: INPE, 2001. Disponível em: http://www.dpi.inpe.br/gilberto/livro/introd/.

CLARK, P. J.; EVANS, F. C. Distance to nearest neighbor as a measure of spatial relationships
in populations. *Ecology*, v. 35, n. 4, p. 445–453, 1954.

GOLDBERG, D. W.; WILSON, J. P.; KNOBLOCK, C. A. From text to geographic coordinates: the
current state of geocoding. *URISA Journal*, v. 19, n. 1, p. 33–46, 2007.

GOODCHILD, M. F. Citizens as sensors: the world of volunteered geography. *GeoJournal*, v. 69,
n. 4, p. 211–221, 2007.

HAKLAY, M. How good is volunteered geographical information? A comparative study of
OpenStreetMap and Ordnance Survey datasets. *Environment and Planning B: Planning and Design*,
v. 37, n. 4, p. 682–703, 2010.

IBGE. *Malha Municipal 2022*. Rio de Janeiro: IBGE, 2023. Disponível em:
https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais.html.

IBGE. *Censo Demográfico 2022: Malha de Setores Censitários — Bairros*. Rio de Janeiro: IBGE,
2024. Disponível em:
https://www.ibge.gov.br/geociencias/organizacao-do-territorio/malhas-territoriais/26565-malhas-de-setores-censitarios-divisoes-intramunicipais.html.

LONGLEY, P. A.; GOODCHILD, M. F.; MAGUIRE, D. J.; RHIND, D. W. *Geographic information
science and systems*. 4. ed. Hoboken: Wiley, 2015.

OPENSHAW, S. *The modifiable areal unit problem*. Norwich: Geo Books, 1984. (Concepts and
Techniques in Modern Geography, 38).

OPENSTREETMAP WIKI. *Overpass API*. Disponível em: https://wiki.openstreetmap.org/wiki/Overpass_API.
Acesso em: 17 nov. 2026.

SLOCUM, T. A.; MCMASTER, R. B.; KESSLER, F. C.; HOWARD, H. H. *Thematic cartography and
geovisualization*. 3. ed. Upper Saddle River: Pearson Prentice Hall, 2009.

TOBLER, W. R. A computer movie simulating urban growth in the Detroit region. *Economic
Geography*, v. 46, sup. 1, p. 234–240, 1970.
