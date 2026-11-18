# Histórico de versões

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

## [1.4.0] — 2026-11-18
### Adicionado
- Comparação com o CNES (Ministério da Saúde): 33 unidades públicas de saúde numa camada
  própria (desligada ao abrir, fora das contagens), com balão, legenda e opção em Camadas, nos
  dois mapas.
- Completude do OSM na saúde: 5 de 22 postos de atenção básica do CNES estão no OSM; bairros
  "vazios" com posto público (Alpino, Rio Vermelho Povoado); tabela por bairro e
  `cnes_unidades.csv`.
- Regra de correspondência CNES × OSM por nome e distância, ajustada em pares reais.
- 56 testes automatizados; teste de interface com 26 verificações.

## [1.3.0] — 2026-11-18
### Adicionado
- População do Censo 2022 por bairro e município (IBGE, Agregados – básico, V0001), baixada
  automaticamente e ligada pelo código do bairro.
- Taxa de estabelecimentos por 10 mil habitantes: tabela, relatório, CSV, coroplético "Por
  habitante" nos dois mapas, população no balão do bairro e na região "fora dos bairros".
- Aviso de taxa instável para bairros com menos de 500 moradores.
### Corrigido
- Mapa clássico listava só um dos 4 bairros empatados em "menor quantidade/densidade".
- Rótulos "Malha 2022" restantes atualizados para a Malha Municipal 2025.
### Alterado
- CI: `actions/checkout` e `actions/setup-python` na versão 7.

## [1.2.0] — 2026-11-18
### Adicionado
- Teste de significância de Monte Carlo no índice de Clark-Evans (999 sorteios na área real
  dos bairros); padrão declarado só com p < 0,05.
- Região "fora dos bairros" (área rural e lacunas) com quantidade e densidade próprias.
- Endereços aproximados por geocodificação reversa (Nominatim) para 128 registros.
- Teste de interface em navegador real (`tests/ui/`), CI no GitHub Actions, Dependabot,
  `SECURITY.md`, versões fixadas (`requirements-lock.txt`) e `.gitattributes`.
- Aviso de vencimento da chave da Esri; ícone e metadados de compartilhamento do site.
### Corrigido
- Escolha da coleta do OSM pela data dos dados (uma exportação manual antiga vencia sempre).
- Empates em "menor quantidade/densidade" agora listados no relatório.
- Relevo 3D ao inclinar o mapa; botão 3D legível; legenda sem cobrir controles em telas estreitas.
- Satélite Esri limitado ao nível 18 (o 19 não existe em SBS e causava falhas).

## [1.1.0] — 2026-11-17
### Adicionado
- Mapa em MapLibre GL JS: mapa vetorial, satélite (Esri e Sentinel-2), híbrido, relevo e
  terreno 3D com elevação real; ícones por categoria; clusters com composição.
- Limite municipal da Malha 2025 do IBGE; mapa enquadrado no município inteiro.
### Alterado
- Regras de classificação refinadas (centros comunitários e jardins sem nome).

## [1.0.0] — 2026-11-17
### Adicionado
- Pipeline completo com dados reais do IBGE e do OpenStreetMap, indicadores por bairro,
  relatórios e mapa interativo (Folium/Leaflet).
