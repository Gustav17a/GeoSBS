"""Geocodificação (endereço → coordenada) e geocodificação reversa com Geopy.

Usa o Nominatim (OpenStreetMap). Política de uso: no máximo 1 requisição por
segundo e User-Agent identificável. Por isso:
- RateLimiter garante o intervalo mínimo entre chamadas;
- todos os resultados ficam em cache (data/raw/geocode_cache.json), e um
  endereço nunca é consultado duas vezes.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import pandas as pd
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

from config import settings

log = logging.getLogger(__name__)
CACHE_FILE = settings.RAW_DIR / "geocode_cache.json"
MANUAL_POINTS_FILE = settings.RAW_DIR / "pontos_manuais.csv"


class Geocoder:
    def __init__(self, cache_file: Path = CACHE_FILE):
        self.cache_file = cache_file
        self.cache: dict[str, dict | None] = (
            json.loads(cache_file.read_text(encoding="utf-8")) if cache_file.exists() else {}
        )
        self._geolocator = None

    def _client(self):
        if self._geolocator is None:
            geolocator = Nominatim(user_agent=settings.HTTP_USER_AGENT, timeout=20)
            self._geolocator = (
                RateLimiter(geolocator.geocode, min_delay_seconds=1.1, max_retries=2),
                RateLimiter(geolocator.reverse, min_delay_seconds=1.1, max_retries=2),
            )
        return self._geolocator

    def save(self) -> None:
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(json.dumps(self.cache, ensure_ascii=False, indent=1), encoding="utf-8")

    def geocode(self, address: str) -> dict | None:
        """Endereço → {'lat', 'lon', 'endereco_encontrado'} ou None."""
        query = f"{address}, {settings.MUNICIPIO_NOME} - {settings.MUNICIPIO_UF}, Brasil"
        key = f"fwd|{query}"
        if key not in self.cache:
            loc = self._client()[0](query, country_codes="br")
            self.cache[key] = (
                {"lat": loc.latitude, "lon": loc.longitude, "endereco_encontrado": loc.address}
                if loc else None
            )
        return self.cache[key]

    def reverse(self, lat: float, lon: float, online: bool = True) -> str | None:
        """Coordenada → endereço textual (rua e número).

        O bairro NÃO é incluído: o bairro de cada ponto vem da junção espacial com a
        malha do IBGE, e o "suburb" do Nominatim (OSM) pode ser diferente dele.
        Com online=False, só consulta o cache (nenhuma requisição é feita).
        """
        key = f"rev|{lat:.6f},{lon:.6f}"
        if key not in self.cache:
            if not online:
                return None
            loc = self._client()[1]((lat, lon), language="pt-BR", zoom=18)
            addr = (loc.raw or {}).get("address", {}) if loc else {}
            parts = [addr.get("road"), addr.get("house_number")]
            text = ", ".join(p for p in parts if p)
            self.cache[key] = text or None
        return self.cache[key]


def load_manual_points(geocoder: Geocoder | None = None) -> pd.DataFrame:
    """Lê data/raw/pontos_manuais.csv (se existir) e geocodifica linhas sem lat/lon.

    Colunas: nome;categoria;endereco;lat;lon;fonte
    `categoria` deve ser um id de config/categories.json (ex.: saude).
    Permite complementar a base com registros conferidos em campo ou em sites
    oficiais, sempre com a fonte informada.
    """
    if not MANUAL_POINTS_FILE.exists():
        return pd.DataFrame()
    df = pd.read_csv(MANUAL_POINTS_FILE, sep=";", dtype=str, encoding="utf-8-sig")
    geocoder = geocoder or Geocoder()
    rows = []
    for i, r in df.iterrows():
        lat, lon, method = r.get("lat"), r.get("lon"), "informada"
        if pd.isna(lat) or pd.isna(lon):
            found = geocoder.geocode(r["endereco"]) if pd.notna(r.get("endereco")) else None
            if not found:
                log.warning("Não foi possível geocodificar: %s", r.get("endereco"))
                continue
            lat, lon, method = found["lat"], found["lon"], "geocodificada"
        rows.append({
            "id": f"manual:{i + 1}", "nome": r.get("nome"), "categoria": r["categoria"],
            "subcategoria": "manual", "endereco": r.get("endereco"),
            "lat": float(lat), "lon": float(lon), "fonte": r.get("fonte") or "Cadastro manual",
            "id_fonte": f"manual:{i + 1}", "tipo_geometria": "node",
            "data_coleta": None, "flags": f"coordenada_{method}",
        })
    geocoder.save()
    return pd.DataFrame(rows)


def fill_missing_addresses(df: pd.DataFrame, limit: int | None = None, online: bool = True,
                           geocoder: Geocoder | None = None) -> pd.DataFrame:
    """Geocodificação reversa para registros sem endereço.

    online=True consulta o Nominatim (lento: ~1,1 s por registro novo, com cache).
    online=False só reaproveita o cache, sem nenhuma requisição: assim os endereços
    já obtidos continuam no mapa em execuções sem --reverse-geocode.
    """
    geocoder = geocoder or Geocoder()
    df = df.copy()
    missing = df.index[df["endereco"].isna()]
    if limit:
        missing = missing[:limit]
    if online:
        novos = sum(f"rev|{df.at[i, 'lat']:.6f},{df.at[i, 'lon']:.6f}" not in geocoder.cache for i in missing)
        log.info("Geocodificação reversa: %d sem endereço, %d novos (~%d s)", len(missing), novos, int(novos * 1.1))
    try:
        for n, idx in enumerate(missing, 1):
            addr = geocoder.reverse(df.at[idx, "lat"], df.at[idx, "lon"], online=online)
            if addr:
                df.at[idx, "endereco"] = f"{addr} (aprox., geocodificação reversa)"
            if online and n % 25 == 0:
                geocoder.save()
    finally:
        if online:
            geocoder.save()
    return df
