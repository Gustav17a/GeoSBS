"""GeoSBS — Plataforma de Inteligência Geográfica de São Bento do Sul.

Uso (na raiz do projeto, com o ambiente virtual ativado):
    python main.py              # usa dados em cache quando existirem
    python main.py --refresh    # força nova coleta no OpenStreetMap
    python main.py --refresh-ibge   # baixa de novo as malhas do IBGE
"""
from __future__ import annotations

import argparse
import logging
import shutil
import sys
import webbrowser
from datetime import date

import pandas as pd

from config import settings
from src.analytics import indicators
from src.analytics.report import write_reports
from src.data_collection import cnes, ibge, osm
from src.data_processing.deduplicate import remove_duplicates
from src.data_processing.normalize import osm_to_dataframe
from src.data_processing.validate import validate
from src.geospatial.geocoding import fill_missing_addresses, load_manual_points
from src.geospatial.spatial import assign_bairro
from src.visualization.map_builder import build_map
from src.visualization.maplibre_builder import build_web_map

log = logging.getLogger("geosbs")


def check_esri_key(today: date | None = None) -> str | None:
    """Aviso quando a chave da Esri estiver perto de vencer (ou vencida)."""
    if not settings.ESRI_API_KEY:
        return "Sem chave da Esri: o satélite do mapa será o Sentinel-2 (10 m). Ver README."
    if not settings.ESRI_KEY_EXPIRES:
        return None
    try:
        expires = date.fromisoformat(settings.ESRI_KEY_EXPIRES)
    except ValueError:
        return f"GEOSBS_ESRI_KEY_EXPIRA inválida ({settings.ESRI_KEY_EXPIRES}); use AAAA-MM-DD."
    days = (expires - (today or date.today())).days
    if days < 0:
        return (f"A chave da Esri VENCEU em {expires:%d/%m/%Y}: o mapa usa o Sentinel-2. "
                "Gere outra no painel da Esri, atualize o .env e rode de novo.")
    if days <= settings.ESRI_KEY_WARN_DAYS:
        return f"A chave da Esri vence em {days} dias ({expires:%d/%m/%Y}). Renove no painel da Esri."
    return None


def run(refresh_osm: bool, refresh_ibge: bool, open_browser: bool,
        reverse_geocode: bool = False) -> int:
    log.info("1/6 Carregando malhas do IBGE")
    municipio = ibge.load_municipio(refresh_ibge)
    bairros = ibge.load_bairros(refresh_ibge)
    populacao, pop_municipio = ibge.load_populacao(refresh_ibge)
    log.info("    Município: %s | bairros: %d", municipio.iloc[0]["NM_MUN"], len(bairros))
    log.info("    População (Censo 2022): %s no município, %s nos bairros",
             pop_municipio, int(populacao["populacao"].sum()))

    log.info("2/6 Coletando pontos no OpenStreetMap")
    bbox_web = municipio.to_crs(settings.CRS_WEB).total_bounds  # minx, miny, maxx, maxy
    raw_file = osm.fetch((bbox_web[1], bbox_web[0], bbox_web[3], bbox_web[2]), force=refresh_osm)
    # CNES: fonte oficial de comparação (não entra nas contagens). Falha não interrompe o pipeline.
    units = None
    try:
        units = cnes.load_units(cnes.fetch(force=refresh_osm), municipio)
        log.info("    CNES: %d unidades públicas de saúde no município (cadastro com %d estabelecimentos)",
                 len(units), units.attrs["cadastro_total"])
    except Exception as exc:  # API fora do ar e sem cache: o mapa sai sem a camada do CNES
        log.warning("    CNES indisponível (%s): o mapa será gerado sem a camada de comparação.", exc)

    log.info("3/6 Padronizando, validando e removendo duplicatas")
    df = osm_to_dataframe(raw_file)
    collection = {"elementos_osm": df.attrs["elementos_osm"],
                  "descartados_pelas_regras": df.attrs["descartados_pelas_regras"]}
    manual = load_manual_points()
    if not manual.empty:
        log.info("    + %d pontos do cadastro manual", len(manual))
        df = pd.concat([df, manual], ignore_index=True)
    pois, rejected, quality = validate(df, municipio)
    quality = {**collection, **quality}
    # Endereços aproximados: com --reverse-geocode consulta o Nominatim; sem a opção,
    # reaproveita apenas o cache (nenhuma requisição), para não perder o que já foi obtido.
    pois = fill_missing_addresses(pois, online=reverse_geocode)
    filled = pois["endereco"].notna() & pois["flags"].str.contains("sem_endereco")
    pois.loc[filled, "flags"] = pois.loc[filled, "flags"].str.replace("sem_endereco", "endereco_aproximado")
    pois, duplicates = remove_duplicates(pois)
    quality["duplicatas_removidas"] = len(duplicates)
    # Contado após a deduplicação, para bater com os registros do mapa.
    quality["enderecos_aproximados"] = int(pois["flags"].str.contains("endereco_aproximado").sum())
    quality["sem_endereco_final"] = int(pois["endereco"].isna().sum())
    quality["registros_finais"] = len(pois)

    log.info("4/6 Atribuindo bairros por junção espacial")
    pois = assign_bairro(pois, bairros)
    if units is not None and not units.empty:
        attrs = dict(units.attrs)
        units = assign_bairro(units, bairros)
        units.attrs = attrs
    settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    pois.to_file(settings.PROCESSED_DIR / "pois.geojson", driver="GeoJSON")
    bairros.to_file(settings.PROCESSED_DIR / "bairros.geojson", driver="GeoJSON")
    pois.drop(columns="geometry").to_csv(settings.PROCESSED_DIR / "pois.csv", index=False,
                                         encoding="utf-8-sig", sep=";")

    log.info("5/6 Calculando indicadores e análises")
    table = indicators.by_bairro(pois, bairros, populacao)
    summary = indicators.summary(pois, table)
    summary["regioes"] = indicators.regions(pois, municipio, table, pop_municipio)
    proximity = indicators.proximity(pois, bairros)
    patterns = indicators.spatial_patterns(pois, bairros)
    summary["cnes"], cnes_detail = indicators.cnes_completeness(units, pois, table)
    summary["bairros_situacao"] = indicators.bairros_overview(table, summary["cnes"])
    for path in write_reports(summary, table, proximity, patterns, quality, duplicates, rejected,
                              cnes_detail=cnes_detail):
        log.info("    Relatório: %s", path.relative_to(settings.ROOT_DIR))

    log.info("6/6 Gerando mapas interativos")
    if (aviso := check_esri_key()):
        log.warning(aviso)
    out = build_web_map(pois, municipio, table, summary, settings.MAP_OUTPUT_FILE, cnes=cnes_detail)
    classic = build_map(pois, municipio, table, summary, settings.MAP_CLASSIC_FILE, cnes=cnes_detail)
    log.info("Mapa principal (MapLibre): %s", out)
    log.info("Mapa clássico (Leaflet):   %s", classic)
    # Mantém a versão publicada no GitHub Pages igual à recém-gerada.
    if settings.PAGES_DIR.exists():
        shutil.copyfile(out, settings.PAGES_DIR / "index.html")
        shutil.copyfile(classic, settings.PAGES_DIR / classic.name)
        log.info("    Cópias atualizadas em %s", settings.PAGES_DIR.relative_to(settings.ROOT_DIR))
    log.info("Resumo: %d estabelecimentos, %d bairros com registros, categoria líder: %s",
             summary["total_estabelecimentos"], summary["bairros_com_registros"],
             summary["categoria_mais_registros"])
    if open_browser:
        webbrowser.open(out.resolve().as_uri())
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="GeoSBS — pipeline de dados e mapa")
    parser.add_argument("--refresh", action="store_true", help="nova coleta no OpenStreetMap")
    parser.add_argument("--refresh-ibge", action="store_true", help="baixar novamente as malhas do IBGE")
    parser.add_argument("--no-browser", action="store_true", help="não abrir o mapa ao final")
    parser.add_argument("--reverse-geocode", action="store_true",
                        help="preencher endereços ausentes via Nominatim (lento: ~1 s por registro)")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)-7s %(message)s", datefmt="%H:%M:%S")
    try:
        return run(args.refresh, args.refresh_ibge, not args.no_browser, args.reverse_geocode)
    except Exception as exc:  # mensagem amigável; detalhes com -v
        log.error("Falha: %s", exc)
        log.debug("Detalhes", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
