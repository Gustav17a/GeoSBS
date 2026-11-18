"""Mapa principal do GeoSBS com MapLibre GL JS (mapa vetorial, satélite, relevo e 3D).

Responsabilidades deste módulo (Python):
- Preparar os dados para exibição: GeoJSON com coordenadas arredondadas a
  6 casas decimais (~0,1 m) e polígonos simplificados com tolerância de
  DISPLAY_SIMPLIFY_M metros. A simplificação é SÓ visual: áreas, junções e
  indicadores já foram calculados antes, com a geometria original.
- Montar as quebras de classe dos coropléticos (mesmas do mapa clássico).
- Embutir os ícones Lucide (SVG, licença ISC) de cada categoria.
- Renderizar o template templates/maplibre.html num único arquivo HTML.

Toda a interação (camadas, filtros, 3D) é JavaScript no template.
"""
from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import geopandas as gpd
import pandas as pd
import numpy as np
import shapely
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import settings
from src.analytics.indicators import establishments
from src.data_collection.categories import load_categories
from src.visualization.map_builder import SEQ_COLORS, class_breaks, legend_bins

# Versão fixa: evita que uma atualização da biblioteca mude o mapa sem aviso.
MAPLIBRE_VERSION = "5.24.1"
MAPLIBRE_JS = f"https://unpkg.com/maplibre-gl@{MAPLIBRE_VERSION}/dist/maplibre-gl.js"
MAPLIBRE_CSS = f"https://unpkg.com/maplibre-gl@{MAPLIBRE_VERSION}/dist/maplibre-gl.css"

ICONS_DIR = Path(__file__).resolve().parent / "icons"
COORD_DECIMALS = 6          # ~0,1 m no equador; suficiente para exibição
DISPLAY_SIMPLIFY_M = 2.0    # tolerância de simplificação dos polígonos (m)


def _round_geom(geom):
    return shapely.transform(geom, lambda c: np.round(c, COORD_DECIMALS))


def display_polygons(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Simplifica (em metros, preservando a topologia) e arredonda para o mapa web."""
    out = gdf.to_crs(settings.CRS_METRIC).copy()
    out["geometry"] = out.geometry.simplify(DISPLAY_SIMPLIFY_M, preserve_topology=True)
    out = out.to_crs(settings.CRS_WEB)
    out["geometry"] = out.geometry.apply(_round_geom)
    return out


def _clean(value):
    """Converte NaN/None em None e tipos NumPy em tipos nativos (JSON)."""
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def _jsonable(obj):
    """Versão serializável em JSON de dicionários/listas com valores NumPy."""
    if isinstance(obj, dict):
        return {str(k): _jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_jsonable(v) for v in obj]
    return _clean(obj)


def _features(gdf: gpd.GeoDataFrame, props: dict[str, str]) -> dict:
    feats = []
    for row in gdf.itertuples(index=False):
        feats.append({
            "type": "Feature",
            "geometry": shapely.geometry.mapping(row.geometry),
            "properties": {out: _clean(getattr(row, col)) for out, col in props.items()},
        })
    return {"type": "FeatureCollection", "features": feats}


def lucide_inner_svg(name: str) -> str:
    """Conteúdo interno (paths) de um ícone Lucide, sem a tag <svg> externa."""
    path = ICONS_DIR / f"{name}.svg"
    if not name or not path.exists():
        return '<circle cx="12" cy="12" r="4"/>'
    text = path.read_text(encoding="utf-8")
    match = re.search(r"<svg[^>]*>(.*)</svg>", text, flags=re.S)
    inner = match.group(1) if match else ""
    return re.sub(r"\s+", " ", inner).strip()


def _bounds(gdf: gpd.GeoDataFrame) -> list[list[float]]:
    minx, miny, maxx, maxy = gdf.to_crs(settings.CRS_WEB).total_bounds
    return [[round(minx, 5), round(miny, 5)], [round(maxx, 5), round(maxy, 5)]]


def focus_geometry(municipio: gpd.GeoDataFrame) -> tuple[dict, list[list[float]]]:
    """Máscara (área de navegação menos o município) e limites de navegação do mapa.

    A máscara cobre os municípios vizinhos com um véu discreto, mantendo-os como
    contexto; os limites impedem que o usuário se afaste da região de interesse.
    """
    mun = municipio.to_crs(settings.CRS_WEB)
    minx, miny, maxx, maxy = mun.total_bounds
    mx, my = (maxx - minx) * settings.MAP_NAV_MARGIN, (maxy - miny) * settings.MAP_NAV_MARGIN
    nav = [[round(minx - mx, 5), round(miny - my, 5)], [round(maxx + mx, 5), round(maxy + my, 5)]]
    outer = shapely.geometry.box(minx - 4 * mx, miny - 4 * my, maxx + 4 * mx, maxy + 4 * my)
    hole = display_polygons(municipio).geometry.union_all()
    mask = _round_geom(outer.difference(hole))
    return ({"type": "FeatureCollection", "features": [
        {"type": "Feature", "geometry": shapely.geometry.mapping(mask), "properties": {}}]}, nav)


def build_data(pois: gpd.GeoDataFrame, municipio: gpd.GeoDataFrame,
               table: gpd.GeoDataFrame, summary: dict) -> dict:
    """Reúne tudo o que o mapa precisa num único dicionário serializável."""
    cats = load_categories()
    labels = {c.id: c.label for c in cats}

    pts = pois.to_crs(settings.CRS_WEB).copy()
    not_est = pts["subcategoria"].isin(settings.NOT_ESTABLISHMENT_SUBCATEGORIES)
    pts["geometry"] = pts.geometry.apply(_round_geom)
    pts["categoria_label"] = pts["categoria"].map(labels)
    pts["estab"] = ~not_est
    poi_props = {"id": "id", "nome": "nome", "cat": "categoria", "label": "categoria_label",
                 "tag": "subcategoria", "endereco": "endereco", "bairro": "bairro",
                 "fonte": "fonte", "id_fonte": "id_fonte", "lat": "lat", "lon": "lon",
                 "estab": "estab"}

    has_pop = "por_10mil_hab" in table
    pop_cols = ["populacao", "por_10mil_hab", "taxa_instavel"] if has_pop else []
    bairros_web = display_polygons(table[["NM_BAIRRO", "total", "densidade_km2",
                                          "area_km2", *pop_cols, "geometry"]])
    bairro_list = []
    for row in table.to_crs(settings.CRS_WEB).itertuples(index=False):
        minx, miny, maxx, maxy = row.geometry.bounds
        bairro_list.append({"nome": row.NM_BAIRRO,
                            "bbox": [round(minx, 5), round(miny, 5), round(maxx, 5), round(maxy, 5)]})
    bairro_list.sort(key=lambda b: b["nome"])

    est = establishments(pois)
    counts = est["categoria"].value_counts()
    n_stops = int(not_est.sum())

    mask, nav_bounds = focus_geometry(municipio)
    count_breaks = class_breaks(table["total"].to_numpy())
    dens_breaks = class_breaks(table["densidade_km2"].to_numpy())
    choropleth = {
        "colors": SEQ_COLORS,
        "total": {"breaks": count_breaks, "bins": legend_bins(count_breaks, 0),
                  "title": "Estabelecimentos por bairro"},
        "dens": {"breaks": dens_breaks, "bins": legend_bins(dens_breaks, 1),
                 "title": "Estabelecimentos por km²"},
    }
    bairro_props = {"nome": "NM_BAIRRO", "total": "total", "dens": "densidade_km2", "area": "area_km2"}
    if has_pop:
        hab_breaks = class_breaks(table["por_10mil_hab"].fillna(0).to_numpy())
        choropleth["hab"] = {"breaks": hab_breaks, "bins": legend_bins(hab_breaks, 1),
                             "title": "Estabelecimentos por 10 mil habitantes",
                             "instaveis": table.loc[table["taxa_instavel"], "NM_BAIRRO"].tolist(),
                             "popMin": settings.POP_MIN_TAXA}
        bairro_props |= {"pop": "populacao", "hab": "por_10mil_hab", "inst": "taxa_instavel"}

    return {
        "categories": [
            {"id": c.id, "label": c.label, "hex": c.hex, "svg": lucide_inner_svg(c.lucide),
             "count": int(counts.get(c.id, 0)),
             "stops": n_stops if c.id == "transporte" else 0}
            for c in cats
        ],
        "pois": _features(pts[~not_est], poi_props),
        "paradas": _features(pts[not_est], poi_props),
        "bairros": _features(bairros_web, bairro_props),
        "municipio": _features(display_polygons(municipio[["NM_MUN", "geometry"]]),
                               {"nome": "NM_MUN"}),
        "bairroList": bairro_list,
        "bounds": {"urbano": _bounds(table), "municipio": _bounds(municipio), "max": nav_bounds},
        "mask": mask,
        "areaMunicipioKm2": round(float(municipio.to_crs(settings.CRS_METRIC).area.sum()) / 1e6, 2),
        "areaBairrosKm2": round(float(table["area_km2"].sum()), 1),
        "choropleth": choropleth,
        "summary": _jsonable(summary),
        "topBairros": [{"nome": r["NM_BAIRRO"], "total": int(r["total"]), "dens": float(r["densidade_km2"]),
                        "hab": (float(r["por_10mil_hab"]) if has_pop and pd.notna(r["por_10mil_hab"]) else None)}
                       for _, r in table.head(5).iterrows()],
    }


def build_web_map(pois: gpd.GeoDataFrame, municipio: gpd.GeoDataFrame,
                  table: gpd.GeoDataFrame, summary: dict, output: Path,
                  esri_key: str | None = None) -> Path:
    """Gera o HTML. `esri_key=None` usa a chave configurada (settings.ESRI_API_KEY)."""
    data = build_data(pois, municipio, table, summary)
    env = Environment(loader=FileSystemLoader(settings.TEMPLATES_DIR),
                      autoescape=select_autoescape(["html"]))
    html = env.get_template("maplibre.html").render(
        data=data,
        s=data["summary"],
        categories=data["categories"],
        maplibre_js=MAPLIBRE_JS,
        maplibre_css=MAPLIBRE_CSS,
        esri_key=settings.ESRI_API_KEY if esri_key is None else esri_key,
        generated_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    return output
