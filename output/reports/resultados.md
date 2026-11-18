# GeoSBS — Resultados gerados automaticamente

Coleta OSM: 2026-11-17T17:41:17. Todos os números abaixo foram calculados pelo pipeline.

## Qualidade dos dados
| verificação | registros |
|---|---|
| elementos_osm | 235 |
| descartados_pelas_regras | 17 |
| registros_recebidos | 218 |
| coordenada_invalida | 0 |
| fora_do_municipio | 45 |
| sem_nome | 72 |
| sem_endereco | 132 |
| duplicatas_removidas | 1 |
| enderecos_aproximados | 128 |
| sem_endereco_final | 3 |
| registros_finais | 172 |

## Indicadores gerais
- Estabelecimentos e equipamentos: **126** (+ 46 paradas de ônibus exibidas apenas no mapa)
- Categoria com mais registros: **Lazer e espaços públicos**
- Bairros analisados: 20 (16 com ao menos um registro)
- Registros fora dos bairros oficiais: 11
- Maior quantidade: **Centro**
- Menor quantidade: **Industrial Sudoeste, Dona Francisca, Alpino, Rio Vermelho Povoado**
- Maior densidade: **Centro**
- Menor densidade: **Industrial Sudoeste, Dona Francisca, Alpino, Rio Vermelho Povoado**
- Maior por habitante: **Centro** (84.0 por 10 mil hab.)
- Menor por habitante: **Dona Francisca, Alpino** (0.0 por 10 mil hab.)

### Por categoria
| Categoria | Registros |
|---|---|
| Farmácias | 7 |
| Saúde | 14 |
| Educação | 26 |
| Segurança pública | 4 |
| Transporte | 5 |
| Serviços públicos | 17 |
| Lazer e espaços públicos | 34 |
| Outros pontos de interesse | 19 |

## Área urbana × fora dos bairros
| Região | Área (km²) | Estabelecimentos | Por km² | % da área | % dos registros | População | Por 10 mil hab. |
|---|---|---|---|---|---|---|---|
| Área urbana (bairros do IBGE) | 82.1 | 115 | 1.4 | 16.6 | 91.3 | 77798 | 14.8 |
| Fora dos bairros (área rural e lacunas) | 412.8 | 11 | 0.03 | 83.4 | 8.7 | 5479 | 20.1 |

Fora dos bairros, por categoria: Outros pontos de interesse 9, Educação 1, Serviços públicos 1.

Município inteiro: 83277 habitantes (Censo 2022), 15.1 estabelecimentos por 10 mil habitantes.

## Por bairro (quantidade, densidade e por habitante)
| Bairro | Área (km²) | Total | Por km² | % do total | População | Por 10 mil hab. |
|---|---|---|---|---|---|---|
| Centro | 2.977 | 44 | 14.78 | 38.3 | 5235 | 84.0 |
| Oxford | 2.649 | 15 | 5.66 | 13.0 | 3386 | 44.3 |
| Serra Alta | 12.055 | 11 | 0.91 | 9.6 | 12167 | 9.0 |
| Colonial | 4.969 | 8 | 1.61 | 7.0 | 5955 | 13.4 |
| Centenário | 4.258 | 8 | 1.88 | 7.0 | 5789 | 13.8 |
| Brasília | 6.265 | 5 | 0.8 | 4.3 | 6394 | 7.8 |
| Boehmerwald | 2.909 | 4 | 1.37 | 3.5 | 2161 | 18.5 |
| Mato Preto | 3.087 | 4 | 1.3 | 3.5 | 3481 | 11.5 |
| Schramm | 3.3 | 4 | 1.21 | 3.5 | 4834 | 8.3 |
| Progresso | 6.131 | 3 | 0.49 | 2.6 | 4374 | 6.9 |
| Rio Negro | 3.248 | 3 | 0.92 | 2.6 | 4262 | 7.0 |
| Cruzeiro | 4.748 | 2 | 0.42 | 1.7 | 6551 | 3.1 |
| Lençol | 4.218 | 1 | 0.24 | 0.9 | 3103 | 3.2 |
| Vinte e Cinco de Julho | 3.679 | 1 | 0.27 | 0.9 | 4190 | 2.4 |
| Rio Vermelho - Estação | 2.957 | 1 | 0.34 | 0.9 | 1292 | 7.7 |
| Bela Aliança | 4.556 | 1 | 0.22 | 0.9 | 488 | 20.5 * |
| Industrial Sudoeste | 1.895 | 0 | 0.0 | 0.0 | 93 | 0.0 * |
| Dona Francisca | 4.286 | 0 | 0.0 | 0.0 | 2083 | 0.0 |
| Alpino | 2.789 | 0 | 0.0 | 0.0 | 1659 | 0.0 |
| Rio Vermelho Povoado | 1.135 | 0 | 0.0 | 0.0 | 301 | 0.0 * |

_* Menos de 500 habitantes: um único registro muda muito a taxa; esses bairros ficam fora dos destaques de maior e menor._

_População: Censo 2022 (IBGE, V0001 = total de pessoas). A taxa por bairro não mede o atendimento: um equipamento serve moradores de outros bairros._

## Completude do OSM na saúde (comparação com o CNES)
Fonte oficial: CNES, API de dados abertos do Ministério da Saúde (baixado em 2026-11-18T13:54:07). O cadastro do município tem 333 estabelecimentos; foram selecionadas 38 unidades de atendimento da rede pública (UBS/ESF, CAPS, UPA, centros especializados municipais e hospitais que atendem pelo SUS). Sem coordenada: 3; cadastro duplicado: 1; fora do município: 1. No mapa: **33**. O CNES não entra nas contagens de estabelecimentos.

- Atenção básica: **5 de 22** unidades do CNES têm registro correspondente no OSM.
- Todas as unidades: 6 de 33.
- Bairros sem nenhum registro no OSM, mas com unidade pública de saúde no CNES: **Alpino, Rio Vermelho Povoado**.

| Grupo | Unidades no CNES | Encontradas no OSM |
|---|---|---|
| Atenção básica (UBS/ESF) | 22 | 5 |
| Especializada e saúde mental | 9 | 0 |
| Hospital e urgência | 2 | 1 |

| Bairro | CNES (unidades públicas) | CNES atenção básica | CNES encontradas no OSM | OSM saúde | OSM (todos) |
|---|---|---|---|---|---|
| Centro | 10 | 1 | 2 | 6 | 44 |
| Oxford | 0 | 0 | 0 | 0 | 15 |
| Serra Alta | 4 | 4 | 0 | 1 | 11 |
| Colonial | 2 | 2 | 1 | 2 | 8 |
| Centenário | 3 | 2 | 0 | 0 | 8 |
| Brasília | 1 | 1 | 0 | 0 | 5 |
| Boehmerwald | 1 | 1 | 1 | 1 | 4 |
| Mato Preto | 1 | 1 | 0 | 0 | 4 |
| Schramm | 1 | 1 | 1 | 3 | 4 |
| Progresso | 2 | 1 | 1 | 1 | 3 |
| Rio Negro | 0 | 0 | 0 | 0 | 3 |
| Cruzeiro | 2 | 2 | 0 | 0 | 2 |
| Lençol | 1 | 1 | 0 | 0 | 1 |
| Vinte e Cinco de Julho | 0 | 0 | 0 | 0 | 1 |
| Rio Vermelho - Estação | 1 | 1 | 0 | 0 | 1 |
| Bela Aliança | 1 | 1 | 0 | 0 | 1 |
| Industrial Sudoeste | 0 | 0 | 0 | 0 | 0 |
| Dona Francisca | 0 | 0 | 0 | 0 | 0 |
| Alpino | 1 | 1 | 0 | 0 | 0 |
| Rio Vermelho Povoado | 1 | 1 | 0 | 0 | 0 |
| Fora dos bairros oficiais | 1 | 1 | 0 | 0 | 11 |

_Correspondência: registro do OSM com nome → ao menos uma palavra própria em comum e até 1000 m; registro sem nome → até 250 m (só atenção básica). Coordenadas do CNES são informadas pelo próprio estabelecimento e podem ter erro; detalhes por unidade em `cnes_unidades.csv`._

## Proximidade (ponto representativo do bairro → unidade mais próxima, em metros, linha reta)
| Bairro | dist_saude_m | dist_educacao_m | dist_farmacias_m |
|---|---|---|---|
| Vinte e Cinco de Julho | 1101.0 | 649.0 | 1085.0 |
| Rio Negro | 1004.0 | 1265.0 | 1607.0 |
| Lençol | 4657.0 | 1769.0 | 6073.0 |
| Colonial | 1341.0 | 1086.0 | 1870.0 |
| Oxford | 1577.0 | 751.0 | 769.0 |
| Progresso | 924.0 | 1288.0 | 1786.0 |
| Centro | 246.0 | 84.0 | 116.0 |
| Centenário | 3834.0 | 1560.0 | 3102.0 |
| Mato Preto | 2931.0 | 487.0 | 2159.0 |
| Dona Francisca | 3210.0 | 2438.0 | 3658.0 |
| Industrial Sudoeste | 1698.0 | 2663.0 | 3365.0 |
| Brasília | 2675.0 | 218.0 | 2323.0 |
| Serra Alta | 2582.0 | 509.0 | 603.0 |
| Boehmerwald | 568.0 | 578.0 | 1657.0 |
| Schramm | 230.0 | 1308.0 | 1213.0 |
| Rio Vermelho - Estação | 4036.0 | 4020.0 | 5121.0 |
| Cruzeiro | 1518.0 | 335.0 | 1247.0 |
| Alpino | 4146.0 | 1849.0 | 4326.0 |
| Rio Vermelho Povoado | 5481.0 | 4083.0 | 5537.0 |
| Bela Aliança | 4155.0 | 1457.0 | 4257.0 |

## Padrão espacial (índice do vizinho mais próximo de Clark-Evans, teste de Monte Carlo na área dos bairros)
| categoria | n | dist_media_obs_m | dist_media_esperada_m | R | p_valor | padrao |
|---|---|---|---|---|---|---|
| Farmácias | 7 | 934.2 | 2389.7 | 0.391 | 0.004 | agrupado |
| Saúde | 14 | 786.8 | 1587.6 | 0.496 | 0.002 | agrupado |
| Educação | 25 | 681.0 | 1153.8 | 0.59 | 0.002 | agrupado |
| Segurança pública | 4 | 1841.5 | 3395.8 | 0.542 | 0.146 | não significativo |
| Transporte | 5 | 1946.6 | 2929.5 | 0.664 | 0.254 | não significativo |
| Serviços públicos | 16 | 425.6 | 1482.4 | 0.287 | 0.002 | agrupado |
| Lazer e espaços públicos | 34 | 574.3 | 969.7 | 0.592 | 0.002 | agrupado |
| Outros pontos de interesse | 10 | 881.2 | 1931.4 | 0.456 | 0.006 | agrupado |

_R < 1 sugere agrupamento; R ≈ 1, distribuição aleatória; R > 1, dispersão. Distância esperada = média de 999 sorteios de pontos aleatórios dentro da área real dos bairros (Monte Carlo; inclui efeito de borda e formato irregular). O padrão só é declarado se p < 0,05; caso contrário, "não significativo"._