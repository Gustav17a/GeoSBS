"""Gravação dos resultados em arquivos (JSON, CSV e Markdown)."""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

from config import settings
from src.data_collection.categories import load_categories


def _md_table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for row in df.itertuples(index=False):
        lines.append("| " + " | ".join("" if pd.isna(v) else str(v) for v in row) + " |")
    return "\n".join(lines)


def _regions_md(reg: dict) -> list[str]:
    tab = pd.DataFrame(reg["tabela"]).rename(columns={
        "regiao": "Região", "area_km2": "Área (km²)", "total": "Estabelecimentos",
        "densidade_km2": "Por km²", "pct_area": "% da área", "pct_registros": "% dos registros",
        "populacao": "População", "por_10mil_hab": "Por 10 mil hab."})
    cats = ", ".join(f"{k} {v}" for k, v in reg["fora_por_categoria"].items()) or "nenhum"
    lines = ["## Área urbana × fora dos bairros", _md_table(tab), "",
             f"Fora dos bairros, por categoria: {cats}.", ""]
    if reg.get("populacao_municipio"):
        lines[-1:] = ["", f"Município inteiro: {reg['populacao_municipio']} habitantes (Censo 2022), "
                          f"{reg['por_10mil_hab_municipio']} estabelecimentos por 10 mil habitantes.", ""]
    return lines


def _bairros_md(tab: pd.DataFrame) -> list[str]:
    cols = {"NM_BAIRRO": "Bairro", "area_km2": "Área (km²)", "total": "Total",
            "densidade_km2": "Por km²", "participacao_pct": "% do total"}
    if "populacao" in tab:
        cols |= {"populacao": "População", "por_10mil_hab": "Por 10 mil hab."}
    out = tab[list(cols)].rename(columns=cols)
    if "taxa_instavel" in tab:
        out["Por 10 mil hab."] = [f"{v} *" if inst else v
                                  for v, inst in zip(out["Por 10 mil hab."], tab["taxa_instavel"])]
    lines = ["## Por bairro (quantidade, densidade e por habitante)", _md_table(out), ""]
    if "taxa_instavel" in tab and tab["taxa_instavel"].any():
        lines += [f"_* Menos de {settings.POP_MIN_TAXA} habitantes: um único registro muda muito a taxa; "
                  "esses bairros ficam fora dos destaques de maior e menor._", ""]
    lines += ["_População: Censo 2022 (IBGE, V0001 = total de pessoas). A taxa por bairro não mede o "
              "atendimento: um equipamento serve moradores de outros bairros._", ""]
    return lines


def _names(pick: dict | None) -> str:
    if not pick:
        return "—"
    return ", ".join(pick.get("empatados", [pick["bairro"]]))


def _extremes_md(s: dict) -> list[str]:
    lines = [f"- Maior quantidade: **{_names(s.get('bairro_maior_quantidade'))}**",
             f"- Menor quantidade: **{_names(s.get('bairro_menor_quantidade'))}**",
             f"- Maior densidade: **{_names(s.get('bairro_maior_densidade'))}**",
             f"- Menor densidade: **{_names(s.get('bairro_menor_densidade'))}**"]
    if s.get("bairro_maior_por_hab"):
        lines += [f"- Maior por habitante: **{_names(s['bairro_maior_por_hab'])}** "
                  f"({s['bairro_maior_por_hab']['valor']} por 10 mil hab.)",
                  f"- Menor por habitante: **{_names(s['bairro_menor_por_hab'])}** "
                  f"({s['bairro_menor_por_hab']['valor']} por 10 mil hab.)"]
    return lines


def write_reports(summary: dict, table: gpd.GeoDataFrame, proximity: pd.DataFrame,
                  patterns: pd.DataFrame, quality: dict, duplicates: pd.DataFrame,
                  rejected: pd.DataFrame, out_dir: Path = settings.REPORTS_DIR) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    labels = {c.id: c.label for c in load_categories()}
    paths = []

    p = out_dir / "indicadores.json"
    p.write_text(json.dumps({"indicadores": summary, "qualidade": quality},
                            ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    paths.append(p)

    tab = pd.DataFrame(table.drop(columns="geometry")).rename(columns=labels)
    p = out_dir / "por_bairro.csv"
    # utf-8-sig: o Excel no Windows reconhece acentos corretamente.
    tab.to_csv(p, index=False, encoding="utf-8-sig", sep=";", decimal=",")
    paths.append(p)

    if summary.get("regioes"):
        p = out_dir / "por_regiao.csv"
        pd.DataFrame(summary["regioes"]["tabela"]).to_csv(p, index=False, encoding="utf-8-sig", sep=";", decimal=",")
        paths.append(p)

    p = out_dir / "proximidade.csv"
    proximity.to_csv(p, index=False, encoding="utf-8-sig", sep=";", decimal=",")
    paths.append(p)

    p = out_dir / "duplicatas_removidas.csv"
    duplicates.to_csv(p, index=False, encoding="utf-8-sig", sep=";")
    paths.append(p)

    if not rejected.empty:
        p = out_dir / "registros_rejeitados.csv"
        rejected.to_csv(p, index=False, encoding="utf-8-sig", sep=";")
        paths.append(p)

    md = [
        "# GeoSBS — Resultados gerados automaticamente",
        "",
        f"Coleta OSM: {summary['data_coleta']}. Todos os números abaixo foram calculados pelo pipeline.",
        "",
        "## Qualidade dos dados",
        _md_table(pd.DataFrame([quality]).T.reset_index().rename(columns={"index": "verificação", 0: "registros"})),
        "",
        "## Indicadores gerais",
        f"- Estabelecimentos e equipamentos: **{summary['total_estabelecimentos']}** "
        f"(+ {summary['paradas_onibus']} paradas de ônibus exibidas apenas no mapa)",
        f"- Categoria com mais registros: **{summary['categoria_mais_registros']}**",
        f"- Bairros analisados: {summary['bairros_analisados']} "
        f"({summary['bairros_com_registros']} com ao menos um registro)",
        f"- Registros fora dos bairros oficiais: {summary['fora_dos_bairros']}",
        *_extremes_md(summary),
        "",
        "### Por categoria",
        _md_table(pd.DataFrame(list(summary["por_categoria"].items()), columns=["Categoria", "Registros"])),
        "",
        *(_regions_md(summary["regioes"]) if summary.get("regioes") else []),
        *_bairros_md(tab),
        "## Proximidade (ponto representativo do bairro → unidade mais próxima, em metros, linha reta)",
        _md_table(proximity.rename(columns={"NM_BAIRRO": "Bairro"})),
        "",
        "## Padrão espacial (índice do vizinho mais próximo de Clark-Evans, teste de Monte Carlo na área dos bairros)",
        _md_table(patterns) if not patterns.empty else "_Pontos insuficientes._",
        "",
        "_R < 1 sugere agrupamento; R ≈ 1, distribuição aleatória; R > 1, dispersão. "
        "Distância esperada = média de 999 sorteios de pontos aleatórios dentro da área real dos "
        "bairros (Monte Carlo; inclui efeito de borda e formato irregular). O padrão só é declarado "
        "se p < 0,05; caso contrário, \"não significativo\"._",
    ]
    p = out_dir / "resultados.md"
    p.write_text("\n".join(md), encoding="utf-8")
    paths.append(p)
    return paths
