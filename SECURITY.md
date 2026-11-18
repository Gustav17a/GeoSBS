# Segurança

## O que é público de propósito

O mapa publicado no GitHub Pages é um site estático: tudo o que o navegador usa fica visível
no HTML (`docs/index.html`). Isso inclui a **chave de API da Esri** usada nas imagens de
satélite. Ela não é um segredo no sentido usual e está protegida por configuração:

- **Domínios autorizados:** só funciona em `https://gustav17a.github.io` e `http://localhost`
  (pedidos de outros sites ou sem origem são recusados pela Esri).
- **Privilégios mínimos:** apenas mapas-base (*basemaps*); nenhum acesso a conteúdo da conta.
- **Cota gratuita e vencimento:** limitada ao plano gratuito da ArcGIS Location Platform e com
  data de vencimento; o `main.py` avisa 30 dias antes.

Se a chave for abusada: revogue-a no painel da Esri, gere outra, atualize o `.env` e rode
`python main.py`. Uma chave revogada deixa de funcionar mesmo continuando no histórico do Git.

## O que nunca deve ser versionado

- `.env` (chaves locais) — já está no `.gitignore`, e o CI falha se ele aparecer no repositório.
- `.venv/` (ambiente virtual) e arquivos de cache do Python.
- Os `.zip` do IBGE em `data/shapefiles/` (grandes e baixados de novo pelo pipeline).

## Como relatar um problema de segurança

Use **Security → Report a vulnerability** neste repositório (relato privado do GitHub). Não abra
*issue* pública com detalhes de uma vulnerabilidade.

## Dados

Os dados do projeto são públicos (IBGE e OpenStreetMap). O sistema não coleta dados de
visitantes: o mapa não usa cookies nem rastreadores próprios. Os serviços de mapas usados
(OpenFreeMap, Esri, AWS, unpkg) recebem as requisições normais de qualquer mapa web.
