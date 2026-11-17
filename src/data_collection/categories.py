"""Leitura das regras de categorias (config/categories.json)."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
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
    # Condições extras para uma regra "chave=valor": {tag: valores aceitos}.
    # "*" aceita qualquer valor (a tag só precisa existir).
    conditions: dict[str, dict[str, tuple[str, ...]]] = field(default_factory=dict)


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
            conditions={
                rule: {tag: tuple(vals) for tag, vals in req.items()}
                for rule, req in c.get("conditions", {}).items()
            },
        )
        for c in raw["categories"]
    )


def category_by_id() -> dict[str, Category]:
    return {c.id: c for c in load_categories()}


def classify(tags: dict[str, str]) -> tuple[str, str] | None:
    """Retorna (id_categoria, subcategoria) para um conjunto de tags OSM.

    A subcategoria é o par chave=valor que determinou a classificação,
    útil para auditoria (ex.: 'amenity=school').

    Se a regra tiver condições (campo "conditions" em categories.json) e as
    tags não as atenderem, a categoria é ignorada e as seguintes são testadas.
    """
    for cat in load_categories():
        for key, values in cat.rules.items():
            value = tags.get(key)
            if value in values:
                rule = f"{key}={value}"
                if _meets(tags, cat.conditions.get(rule, {})):
                    return cat.id, rule
    return None


def _meets(tags: dict[str, str], required: dict[str, tuple[str, ...]]) -> bool:
    for tag, accepted in required.items():
        value = (tags.get(tag) or "").strip()
        if not value or ("*" not in accepted and value not in accepted):
            return False
    return True
