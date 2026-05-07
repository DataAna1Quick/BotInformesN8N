"""Extract a brand palette from the client logo using k-means on pixel colors."""
from __future__ import annotations

import colorsys
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError
from sklearn.cluster import KMeans

from .errors import LogoInvalidError


# Defaults if extraction fails or no logo provided.
PROVIDER_YELLOW = "#F4B400"
PROVIDER_BLACK = "#0F1419"
DEFAULT_PRIMARY = "#1B3D7A"


@dataclass
class Palette:
    primary: str = DEFAULT_PRIMARY            # client primary
    accent: str = PROVIDER_YELLOW             # always Quick Help yellow
    dark: str = PROVIDER_BLACK
    white: str = "#FFFFFF"
    pale: str = "#F7F8FB"
    grey_light: str = "#E6E8EE"
    grey: str = "#7A7F8C"
    grey_dark: str = "#3F4452"
    success: str = "#2C7A4E"
    success_light: str = "#5BA77A"
    alert: str = "#C8102E"


@dataclass
class ClientConfig:
    name: str
    subtitle: str = "Visión integral del servicio logístico"
    logo_bytes: bytes | None = None
    palette: Palette = field(default_factory=Palette)


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------

def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*[int(c) for c in rgb])


def _luminance(rgb: tuple[int, int, int]) -> float:
    # Relative luminance (0..1) per WCAG.
    r, g, b = [c / 255.0 for c in rgb]
    def adj(x: float) -> float:
        return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * adj(r) + 0.7152 * adj(g) + 0.0722 * adj(b)


def _saturation(rgb: tuple[int, int, int]) -> float:
    r, g, b = [c / 255.0 for c in rgb]
    _, _, s = colorsys.rgb_to_hsv(r, g, b)
    return s


def _is_neutral(rgb: tuple[int, int, int]) -> bool:
    """Filter near-white, near-black and washed-out greys."""
    lum = _luminance(rgb)
    sat = _saturation(rgb)
    if lum > 0.92 or lum < 0.04:  # near white / near black
        return True
    if sat < 0.18:  # near grey
        return True
    return False


def _pick_primary(clusters: list[tuple[tuple[int, int, int], int]]) -> str:
    """Return the most prominent non-neutral cluster, or fall back to default."""
    # clusters: list of (rgb, count) sorted by count desc
    for rgb, _ in clusters:
        if not _is_neutral(rgb):
            return _rgb_to_hex(rgb)
    return DEFAULT_PRIMARY


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_palette(
    logo: bytes | str | Path | BytesIO | None,
    *,
    n_clusters: int = 6,
    strict: bool = False,
) -> Palette:
    """Build a Palette from the dominant non-neutral colour of a logo.

    - If `logo` is None, returns the default palette silently.
    - If `logo` cannot be parsed and `strict=True`, raises LogoInvalidError.
      Otherwise returns the default palette.
    """
    if logo is None:
        return Palette()

    if isinstance(logo, bytes):
        # Reject obvious non-raster formats up front (SVG/PDF) — PIL can't handle them.
        head = logo[:64].lstrip()
        if head.startswith(b"<?xml") or head.startswith(b"<svg") or head.startswith(b"%PDF"):
            if strict:
                raise LogoInvalidError(
                    "El logo está en un formato vectorial (SVG/PDF) que no es compatible. "
                    "Convierte el logo a PNG o JPG y vuelve a subirlo."
                )
            return Palette()

    try:
        img = Image.open(BytesIO(logo) if isinstance(logo, bytes) else logo)
    except (UnidentifiedImageError, OSError) as e:
        if strict:
            raise LogoInvalidError(
                f"No se pudo leer el logo como imagen: {type(e).__name__}. "
                "Asegúrate de subir un PNG o JPG válido."
            ) from e
        return Palette()

    img = img.convert("RGBA")
    # Drop transparent pixels.
    arr = np.array(img)
    rgba = arr.reshape(-1, 4)
    opaque = rgba[rgba[:, 3] > 32][:, :3]
    if opaque.shape[0] < 32:
        return Palette()

    # Down-sample for speed.
    if opaque.shape[0] > 5000:
        idx = np.random.RandomState(42).choice(opaque.shape[0], 5000, replace=False)
        opaque = opaque[idx]

    n = min(n_clusters, len(opaque))
    if n < 2:
        return Palette()

    km = KMeans(n_clusters=n, n_init=4, random_state=42)
    labels = km.fit_predict(opaque)
    centroids = km.cluster_centers_
    counts = np.bincount(labels, minlength=n)
    order = np.argsort(-counts)
    clusters = [(tuple(centroids[i].astype(int)), int(counts[i])) for i in order]

    primary = _pick_primary(clusters)
    return Palette(primary=primary)
