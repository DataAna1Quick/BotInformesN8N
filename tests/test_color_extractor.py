from core.color_extractor import Palette, extract_palette


def test_extract_palette_with_none_returns_default():
    p = extract_palette(None)
    assert isinstance(p, Palette)
    assert p.primary == "#1B3D7A"
    assert p.accent == "#F4B400"


def test_extract_palette_with_logo_bytes(client_logo_bytes):
    p = extract_palette(client_logo_bytes)
    assert isinstance(p, Palette)
    # Primary color should be a 7-char hex string (e.g. "#1B3D7A").
    assert p.primary.startswith("#") and len(p.primary) == 7
    # Should not be near-white nor near-black.
    rgb = tuple(int(p.primary[i:i+2], 16) for i in (1, 3, 5))
    assert sum(rgb) < 720, "primary too close to white"
    assert sum(rgb) > 60, "primary too close to black"
