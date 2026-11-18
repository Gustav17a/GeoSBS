"""Construção do mapa interativo com Folium.

Camadas (todas controláveis pelo LayerControl):
- Mapas-base: OpenStreetMap e CartoDB Positron.
- Limite municipal e limites dos bairros (IBGE).
- Coropléticos de quantidade e de densidade por bairro.
- Marcadores por categoria dentro de um único MarkerCluster
  (FeatureGroupSubGroup), para que o agrupamento funcione entre categorias.
- Mapa de calor (HeatMap) dos estabelecimentos.
"""
from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path

import folium
import geopandas as gpd
import numpy as np
import pandas as pd
from folium.plugins import FeatureGroupSubGroup, HeatMap, MarkerCluster
from jinja2 import Environment, FileSystemLoader, select_autoescape

from config import settings
from src.analytics.indicators import establishments
from src.data_collection.categories import load_categories

HEAT_LAYER = "Mapa de calor (estabelecimentos)"
CHORO_COUNT = "Coroplético: quantidade por bairro"
CHORO_DENSITY = "Coroplético: densidade (por km²)"
# Paleta sequencial (azul-esverdeado claro → escuro), legível para daltônicos.
# Ícone da aba (SVG embutido, sem requisição extra); o mesmo do mapa principal.
FAVICON = '<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22%20viewBox%3D%220%200%2064%2064%22%3E%3Crect%20width%3D%2264%22%20height%3D%2264%22%20rx%3D%2214%22%20fill%3D%22%23111827%22/%3E%3Cpath%20d%3D%22M32%2012c-8.3%200-15%206.5-15%2014.6C17%2037.5%2032%2052%2032%2052s15-14.5%2015-25.4C47%2018.5%2040.3%2012%2032%2012z%22%20fill%3D%22%2322d3ee%22/%3E%3Ccircle%20cx%3D%2232%22%20cy%3D%2226.5%22%20r%3D%225.5%22%20fill%3D%22%23111827%22/%3E%3C/svg%3E">'
SEQ_COLORS = ["#edf8fb", "#b2e2e2", "#66c2a4", "#2ca25f", "#006d2c"]


def class_breaks(values: np.ndarray, k: int = 5) -> list[float]:
    """Quebras por quantis, sem repetições (bairros com muitos zeros repetem quantis)."""
    values = np.asarray(values, dtype=float)
    if values.size == 0:
        return [0.0, 1.0]
    qs = np.unique(np.quantile(values, np.linspace(0, 1, k + 1)))
    if qs.size < 2:
        qs = np.array([qs[0], qs[0] + 1])
    return qs.tolist()


def color_for(value: float, breaks: list[float]) -> str:
    n_classes = len(breaks) - 1
    palette = SEQ_COLORS[-n_classes:] if n_classes <= len(SEQ_COLORS) else SEQ_COLORS
    for i in range(n_classes):
        if value <= breaks[i + 1]:
            return palette[min(i, len(palette) - 1)]
    return palette[-1]


def legend_bins(breaks: list[float], decimals: int) -> list[dict]:
    fmt = f"{{:.{decimals}f}}"
    return [
        {"color": color_for(breaks[i + 1], breaks),
         "label": f"{fmt.format(breaks[i])}–{fmt.format(breaks[i + 1])}"}
        for i in range(len(breaks) - 1)
    ]


def _has_name(row) -> bool:
    """Nome ausente chega como NaN (float), que é 'verdadeiro' em Python."""
    return pd.notna(row["nome"]) and str(row["nome"]).strip() != ""


def _popup(row) -> folium.Popup:
    def esc(v):
        return html.escape(str(v)) if v is not None and str(v) != "nan" else "<i>não informado</i>"

    if row["fonte"] == "OpenStreetMap":
        source = (f'<a href="https://www.openstreetmap.org/{row["id_fonte"]}" target="_blank">'
                  f'OpenStreetMap ({esc(row["id_fonte"])})</a>')
    else:
        source = esc(row["fonte"])
    body = f"""
    <div style="font-family:Segoe UI,system-ui,sans-serif;font-size:12.5px;min-width:220px">
      <b style="font-size:14px">{esc(row['nome']) if _has_name(row) else '<i>(sem nome no OSM)</i>'}</b>
      <table style="margin-top:6px;border-collapse:collapse">
        <tr><td style="color:#666;padding-right:8px">Categoria</td><td>{esc(row['categoria_label'])}</td></tr>
        <tr><td style="color:#666">Tipo (tag)</td><td><code>{esc(row['subcategoria'])}</code></td></tr>
        <tr><td style="color:#666">Endereço</td><td>{esc(row['endereco'])}</td></tr>
        <tr><td style="color:#666">Bairro</td><td>{esc(row['bairro'])}</td></tr>
        <tr><td style="color:#666">Coordenadas</td><td>{row['lat']:.6f}, {row['lon']:.6f}</td></tr>
        <tr><td style="color:#666">Fonte</td><td>{source}</td></tr>
      </table>
    </div>"""
    return folium.Popup(body, max_width=320)


def _choropleth(m, table, field, name, breaks, fmt):
    def style(feature):
        return {"fillColor": color_for(feature["properties"][field], breaks),
                "color": "#334155", "weight": 1, "fillOpacity": 0.7}

    folium.GeoJson(
        table.to_crs(settings.CRS_WEB)[["NM_BAIRRO", "total", "densidade_km2", "area_km2", "geometry"]],
        name=name,
        style_function=style,
        highlight_function=lambda f: {"weight": 3, "color": "#0f172a"},
        tooltip=folium.GeoJsonTooltip(
            fields=["NM_BAIRRO", "total", "densidade_km2", "area_km2"],
            aliases=["Bairro", "Estabelecimentos", "Densidade (por km²)", "Área (km²)"],
            localize=True,
        ),
        show=False,
    ).add_to(m)


def build_map(pois: gpd.GeoDataFrame, municipio: gpd.GeoDataFrame,
              table: gpd.GeoDataFrame, summary: dict, output: Path) -> Path:
    cats = load_categories()
    labels = {c.id: c.label for c in cats}
    pois = pois.copy()
    pois["categoria_label"] = pois["categoria"].map(labels)

    mun_web = municipio.to_crs(settings.CRS_WEB)
    minx, miny, maxx, maxy = mun_web.total_bounds
    m = folium.Map(location=[(miny + maxy) / 2, (minx + maxx) / 2], zoom_start=12,
                   tiles=None, control_scale=True)
    folium.TileLayer("OpenStreetMap", name="OpenStreetMap").add_to(m)
    # show=False: só o mapa-base padrão é carregado; os demais ficam no LayerControl.
    folium.TileLayer("OpenTopoMap", name="Relevo (OpenTopoMap)", show=False).add_to(m)
    folium.TileLayer("Esri.WorldImagery", name="Imagem de satélite (Esri)", show=False).add_to(m)
    m.fit_bounds([[miny, minx], [maxy, maxx]])

    folium.GeoJson(
        mun_web, name="Limite municipal (IBGE)",
        style_function=lambda f: {"fill": False, "color": "#0f172a", "weight": 3, "dashArray": "6 4"},
    ).add_to(m)

    folium.GeoJson(
        table.to_crs(settings.CRS_WEB)[["NM_BAIRRO", "total", "densidade_km2", "geometry"]],
        name="Bairros (IBGE, Censo 2022)",
        style_function=lambda f: {"fillColor": "#22d3ee", "fillOpacity": 0.04,
                                  "color": "#0891b2", "weight": 1.2},
        highlight_function=lambda f: {"fillOpacity": 0.15, "weight": 2.5},
        tooltip=folium.GeoJsonTooltip(fields=["NM_BAIRRO", "total", "densidade_km2"],
                                      aliases=["Bairro", "Estabelecimentos", "Por km²"]),
    ).add_to(m)

    count_breaks = class_breaks(table["total"].to_numpy())
    dens_breaks = class_breaks(table["densidade_km2"].to_numpy())
    _choropleth(m, table, "total", CHORO_COUNT, count_breaks, "{:.0f}")
    _choropleth(m, table, "densidade_km2", CHORO_DENSITY, dens_breaks, "{:.1f}")

    cluster = MarkerCluster(name="Agrupamento de marcadores", control=False,
                            options={"disableClusteringAtZoom": 18}).add_to(m)
    category_layers, panel_categories = [], []
    est = establishments(pois)
    max_count = max(est["categoria"].value_counts().max() if len(est) else 1, 1)
    for cat in cats:
        subset = pois[pois["categoria"] == cat.id]
        n_est_cat = int((est["categoria"] == cat.id).sum())
        n_extra = len(subset) - n_est_cat          # paradas de ônibus (só em Transporte)
        layer_name = f"{cat.label} ({n_est_cat} + {n_extra} paradas)" if n_extra else f"{cat.label} ({n_est_cat})"
        group = FeatureGroupSubGroup(cluster, name=layer_name).add_to(m)
        for _, row in subset.iterrows():
            folium.Marker(
                [row["lat"], row["lon"]],
                icon=folium.Icon(color=cat.color, icon=cat.icon, prefix="fa"),
                tooltip=row["nome"] if _has_name(row) else f"{cat.label} (sem nome)",
                popup=_popup(row),
            ).add_to(group)
        n_est = int((est["categoria"] == cat.id).sum())
        category_layers.append(f"{cat.label} (")
        panel_categories.append({"label": cat.label, "hex": cat.hex, "count": n_est,
                                 "layer": f"{cat.label} (", "pct": round(100 * n_est / max_count)})

    HeatMap(est[["lat", "lon"]].to_numpy().tolist(), name=HEAT_LAYER, show=False,
            radius=18, blur=22, min_opacity=0.25).add_to(m)

    folium.LayerControl(collapsed=True, position="topright").add_to(m)

    env = Environment(loader=FileSystemLoader(settings.TEMPLATES_DIR),
                      autoescape=select_autoescape(["html"]))
    panel = env.get_template("panel.html").render(
        s=summary,
        categories=panel_categories,
        category_layers=category_layers,
        heat_layer=HEAT_LAYER,
        top_count=table.head(5).to_dict("records"),
        legends=[
            {"title": "Quantidade de estabelecimentos", "bins": legend_bins(count_breaks, 0)},
            {"title": "Densidade (estabelecimentos por km²)", "bins": legend_bins(dens_breaks, 1)},
        ],
        generated_at=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )
    m.get_root().html.add_child(folium.Element(panel))
    m.get_root().header.add_child(folium.Element(
        "<title>GeoSBS · Inteligência Geográfica de São Bento do Sul</title>" + FAVICON))

    output.parent.mkdir(parents=True, exist_ok=True)
    m.save(str(output))
    return output
