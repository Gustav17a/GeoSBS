"""Leitura das regras de categorias (config/categories.json)."""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache

from config import settings


@dataclass(frozen=True)
class Category:
    id: str
    label: str
    color: str
    hex: str
    icon: str
    rules: dict[str, tuple[str, ...]]


@lru_cache(maxsize=1)
def load_categories() -> tuple[Category, ...]:
    with open(settings.CATEGORIES_FILE, encoding="utf-8") as fh:
        raw = json.load(fh)
    return tuple(
        Category(
            id=c["id"],
            label=c["label"],
            color=c["color"],
            hex=c["hex"],
            icon=c["icon"],
            rules={k: tuple(v) for k, v in c["rules"].items()},
        )
        for c in raw["categories"]
    )


def category_by_id() -> dict[str, Category]:
    return {c.id: c for c in load_categories()}


def classify(tags: dict[str, str]) -> tuple[str, str] | None:
    """Retorna (id_categoria, subcategoria) para um conjunto de tags OSM.

    A subcategoria é o par chave=valor que determinou a classificação,
    útil para auditoria (ex.: 'amenity=school').
    """
    for cat in load_categories():
        for key, values in cat.rules.items():
            value = tags.get(key)
            if value in values:
                return cat.id, f"{key}={value}"
    return None
