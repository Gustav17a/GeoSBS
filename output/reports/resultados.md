# GeoSBS — Resultados gerados automaticamente

Coleta OSM: 2026-11-17T17:41:17. Todos os números abaixo foram calculados pelo pipeline.

## Qualidade dos dados
| verificação | registros |
|---|---|
| registros_recebidos | 235 |
| coordenada_invalida | 0 |
| fora_do_municipio | 57 |
| sem_nome | 77 |
| sem_endereco | 137 |
| duplicatas_removidas | 1 |
| registros_finais | 177 |

## Indicadores gerais
- Estabelecimentos e equipamentos: **131** (+ 46 paradas de ônibus exibidas apenas no mapa)
- Categoria com mais registros: **Lazer e espaços públicos**
- Bairros analisados: 20 (16 com ao menos um registro)
- Registros fora dos bairros oficiais: 12

### Por categoria
| Categoria | Registros |
|---|---|
| Farmácias | 7 |
| Saúde | 14 |
| Educação | 26 |
| Segurança pública | 4 |
| Transporte | 5 |
| Serviços públicos | 22 |
| Lazer e espaços públicos | 39 |
| Outros pontos de interesse | 14 |

## Por bairro (quantidade e densidade)
| Bairro | Área (km²) | Total | Por km² | % do total |
|---|---|---|---|---|
| Centro | 2.977 | 46 | 15.45 | 38.7 |
| Oxford | 2.649 | 16 | 6.04 | 13.4 |
| Serra Alta | 12.055 | 11 | 0.91 | 9.2 |
| Colonial | 4.969 | 8 | 1.61 | 6.7 |
| Centenário | 4.258 | 8 | 1.88 | 6.7 |
| Boehmerwald | 2.909 | 5 | 1.72 | 4.2 |
| Brasília | 6.265 | 5 | 0.8 | 4.2 |
| Mato Preto | 3.087 | 4 | 1.3 | 3.4 |
| Schramm | 3.3 | 4 | 1.21 | 3.4 |
| Progresso | 6.131 | 3 | 0.49 | 2.5 |
| Rio Negro | 3.248 | 3 | 0.92 | 2.5 |
| Cruzeiro | 4.748 | 2 | 0.42 | 1.7 |
| Lençol | 4.218 | 1 | 0.24 | 0.8 |
| Vinte e Cinco de Julho | 3.679 | 1 | 0.27 | 0.8 |
| Rio Vermelho - Estação | 2.957 | 1 | 0.34 | 0.8 |
| Bela Aliança | 4.556 | 1 | 0.22 | 0.8 |
| Industrial Sudoeste | 1.895 | 0 | 0.0 | 0.0 |
| Dona Francisca | 4.286 | 0 | 0.0 | 0.0 |
| Alpino | 2.789 | 0 | 0.0 | 0.0 |
| Rio Vermelho Povoado | 1.135 | 0 | 0.0 | 0.0 |

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

## Padrão espacial (índice do vizinho mais próximo de Clark-Evans, área dos bairros)
| categoria | n | dist_media_obs_m | dist_media_esperada_m | R | padrao |
|---|---|---|---|---|---|
| Farmácias | 7 | 934.2 | 1712.5 | 0.546 | agrupado |
| Saúde | 14 | 786.8 | 1210.9 | 0.65 | agrupado |
| Educação | 25 | 681.0 | 906.2 | 0.752 | agrupado |
| Segurança pública | 4 | 1841.5 | 2265.4 | 0.813 | agrupado |
| Transporte | 5 | 1946.6 | 2026.2 | 0.961 | próximo do aleatório |
| Serviços públicos | 18 | 654.5 | 1067.9 | 0.613 | agrupado |
| Lazer e espaços públicos | 38 | 530.0 | 735.0 | 0.721 | agrupado |
| Outros pontos de interesse | 8 | 480.2 | 1601.9 | 0.3 | agrupado |

_R < 1 sugere agrupamento; R ≈ 1, distribuição aleatória; R > 1, dispersão. Sem correção de efeito de borda._