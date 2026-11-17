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

import pandas as pd

from config import settings
from src.analytics import indicators
from src.analytics.report import write_reports
from src.data_collection import ibge, osm
from src.data_processing.deduplicate import remove_duplicates
from src.data_processing.normalize import osm_to_dataframe
from src.data_processing.validate import validate
from src.geospatial.geocoding import fill_missing_addresses, load_manual_points
from src.geospatial.spatial import assign_bairro
from src.visualization.map_builder import build_map
from src.visualization.maplibre_builder import build_web_map

log = logging.getLogger("geosbs")


def run(refresh_osm: bool, refresh_ibge: bool, open_browser: bool,
        reverse_geocode: bool = False) -> int:
    log.info("1/6 Carregando malhas do IBGE")
    municipio = ibge.load_municipio(refresh_ibge)
    bairros = ibge.load_bairros(refresh_ibge)
    log.info("    Município: %s | bairros: %d", municipio.iloc[0]["NM_MUN"], len(bairros))

    log.info("2/6 Coletando pontos no OpenStreetMap")
    bbox_web = municipio.to_crs(settings.CRS_WEB).total_bounds  # minx, miny, maxx, maxy
    raw_file = osm.fetch((bbox_web[1], bbox_web[0], bbox_web[3], bbox_web[2]), force=refresh_osm)

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
    if reverse_geocode:
        pois = fill_missing_addresses(pois)
        filled = pois["endereco"].notna() & pois["flags"].str.contains("sem_endereco")
        pois.loc[filled, "flags"] = pois.loc[filled, "flags"].str.replace(
            "sem_endereco", "endereco_aproximado")
        quality["enderecos_geocodificados"] = int(filled.sum())
    pois, duplicates = remove_duplicates(pois)
    quality["duplicatas_removidas"] = len(duplicates)
    quality["registros_finais"] = len(pois)

    log.info("4/6 Atribuindo bairros por junção espacial")
    pois = assign_bairro(pois, bairros)
    settings.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    pois.to_file(settings.PROCESSED_DIR / "pois.geojson", driver="GeoJSON")
    bairros.to_file(settings.PROCESSED_DIR / "bairros.geojson", driver="GeoJSON")
    pois.drop(columns="geometry").to_csv(settings.PROCESSED_DIR / "pois.csv", index=False,
                                         encoding="utf-8-sig", sep=";")

    log.info("5/6 Calculando indicadores e análises")
    table = indicators.by_bairro(pois, bairros)
    summary = indicators.summary(pois, table)
    proximity = indicators.proximity(pois, bairros)
    patterns = indicators.spatial_patterns(pois, bairros)
    for path in write_reports(summary, table, proximity, patterns, quality, duplicates, rejected):
        log.info("    Relatório: %s", path.relative_to(settings.ROOT_DIR))

    log.info("6/6 Gerando mapas interativos")
    out = build_web_map(pois, municipio, table, summary, settings.MAP_OUTPUT_FILE)
    classic = build_map(pois, municipio, table, summary, settings.MAP_CLASSIC_FILE)
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
