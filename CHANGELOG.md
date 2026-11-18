# Histórico de versões

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).

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
