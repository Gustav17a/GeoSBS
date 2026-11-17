"""Utilitários HTTP com cache em disco e tentativas com espera crescente."""
from __future__ import annotations

import logging
import time
from pathlib import Path

import requests

from config import settings

log = logging.getLogger(__name__)


class DownloadError(RuntimeError):
    """Falha ao obter um recurso remoto depois de todas as tentativas."""


def download_file(url: str, dest: Path, force: bool = False, retries: int = 3) -> Path:
    """Baixa `url` para `dest`, reaproveitando o arquivo se já existir.

    O cache evita requisições repetidas aos servidores públicos.
    """
    if dest.exists() and dest.stat().st_size > 0 and not force:
        log.info("Usando cache: %s", dest.name)
        return dest

    dest.parent.mkdir(parents=True, exist_ok=True)
    headers = {"User-Agent": settings.HTTP_USER_AGENT}
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            log.info("Baixando %s (tentativa %d/%d)", url, attempt, retries)
            with requests.get(url, headers=headers, stream=True, timeout=120) as resp:
                resp.raise_for_status()
                tmp = dest.with_suffix(dest.suffix + ".part")
                with open(tmp, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=1 << 16):
                        fh.write(chunk)
                tmp.replace(dest)
            return dest
        except requests.RequestException as exc:
            last_error = exc
            wait = 5 * attempt
            log.warning("Falha no download (%s). Nova tentativa em %ds.", exc, wait)
            time.sleep(wait)

    raise DownloadError(
        f"Não foi possível baixar {url}: {last_error}. "
        f"Alternativa: baixe manualmente e salve como {dest}"
    )
