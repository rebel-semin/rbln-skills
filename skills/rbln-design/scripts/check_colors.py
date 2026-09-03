#!/usr/bin/env python3
"""Check files against the Rebellions palette and compute text contrast.

Usage:
  check_colors.py FILE [FILE ...]        report hex colors that are not in the palette
  check_colors.py --pair FG BG           contrast ratio + WCAG verdict for one text/background pair
  check_colors.py --matrix               contrast matrix for every palette pair
  check_colors.py --json                 print the palette as JSON

Exit status is 1 when an off-palette color is found in any scanned file, 0 otherwise.
Only the standard library is used. Hex colors are matched as #RGB, #RRGGBB,
0xRRGGBB and OOXML srgbClr val="RRGGBB".
"""
import argparse
import json
import re
import sys

PALETTE = {
    "52F756": "neon-green (point / highlight)",
    "1B1F23": "near-black (text, dark background)",
    "24292F": "dark-gray (series 2, panels, table header)",
    "BBC4CF": "mid-gray (series 3, secondary text)",
    "D9E4ED": "light-blue-gray (series 4, gridlines, borders)",
    "F6F8FA": "off-white (light background, zebra rows)",
    "FFFFFF": "white",
    "174BEB": "secondary blue",
    "9A4EFF": "secondary purple",
    "F7318B": "secondary pink",
    "FF3333": "secondary red",
    "FFD527": "secondary yellow",
}
# The theme file in the deck master stores accent1 as 51F756; treat it as the point color.
ALIASES = {"51F756": "52F756"}

HEX_RE = re.compile(
    r"(?:#|0x|srgbClr\s+val=\")([0-9a-fA-F]{6}|[0-9a-fA-F]{3})(?![0-9a-fA-F])"
)
# Things that look like hex but are not colors (e.g. git SHAs, ids) are filtered by
# requiring the # / 0x / srgbClr prefix above. 8-digit RGBA is ignored by the lookahead.


def normalize(h):
    h = h.upper()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return ALIASES.get(h, h)


def luminance(h):
    def chan(c):
        c = int(c, 16) / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = chan(h[0:2]), chan(h[2:4]), chan(h[4:6])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(fg, bg):
    l1, l2 = luminance(normalize(fg)), luminance(normalize(bg))
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def verdict(ratio):
    if ratio >= 7:
        return "AAA"
    if ratio >= 4.5:
        return "AA"
    if ratio >= 3:
        return "AA-large (>=18pt/24px or bold 14pt/19px) / UI graphics only"
    return "FAIL - not for text"


def scan(paths):
    bad = 0
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError as e:
            print(f"{path}: cannot read ({e})", file=sys.stderr)
            bad += 1
            continue
        seen = {}
        for m in HEX_RE.finditer(text):
            h = normalize(m.group(1))
            line = text.count("\n", 0, m.start()) + 1
            seen.setdefault(h, []).append(line)
        off = {h: ls for h, ls in seen.items() if h not in PALETTE}
        on = {h: ls for h, ls in seen.items() if h in PALETTE}
        print(f"{path}: {len(on)} palette color(s), {len(off)} off-palette")
        for h, ls in sorted(on.items(), key=lambda kv: -len(kv[1])):
            print(f"  ok   #{h}  {PALETTE[h]}  x{len(ls)}")
        for h, ls in sorted(off.items(), key=lambda kv: -len(kv[1])):
            where = ", ".join(str(l) for l in ls[:6]) + (" ..." if len(ls) > 6 else "")
            print(f"  OFF  #{h}  lines {where}")
        if "52F756" in on and len(on["52F756"]) > 1:
            print(f"  note #52F756 appears {len(on['52F756'])} times - confirm it marks ONE highlight")
        bad += len(off)
    return bad


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*")
    ap.add_argument("--pair", nargs=2, metavar=("FG", "BG"))
    ap.add_argument("--matrix", action="store_true")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.json:
        print(json.dumps({("#" + k): v for k, v in PALETTE.items()}, indent=2, ensure_ascii=False))
        return 0
    if a.pair:
        fg, bg = (normalize(x.lstrip("#")) for x in a.pair)
        r = contrast(fg, bg)
        print(f"#{fg} on #{bg}: {r:.2f}:1  {verdict(r)}")
        return 0
    if a.matrix:
        keys = list(PALETTE)
        w = 8
        print(" " * w + "".join(f"{'#'+k:>{w}}" for k in keys))
        for fg in keys:
            row = "".join(f"{contrast(fg, bg):>{w}.1f}" if fg != bg else f"{'-':>{w}}" for bg in keys)
            print(f"{'#'+fg:>{w}}{row}")
        print("\nrows = text/foreground, columns = background. >=4.5 AA body text, >=3.0 large text / graphics.")
        return 0
    if not a.files:
        ap.print_help()
        return 2
    return 1 if scan(a.files) else 0


if __name__ == "__main__":
    sys.exit(main())
