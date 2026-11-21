"""WCAG AA check for every text/background pair in docs/DESIGN.md (run: python3 scripts/check_contrast.py)."""
import sys

PAIRS = [  # (text, background, what)
    ("#1D1424", "#F6F3F8", "ink on canvas"), ("#463A51", "#FFFFFF", "ink-2 on surface"),
    ("#675B72", "#F6F3F8", "muted on canvas"), ("#675B72", "#FFFFFF", "muted on surface"),
    ("#675B72", "#EEE8F2", "muted on surface-2"), ("#FFFFFF", "#6D3B8C", "white on plum-500 button"),
    ("#6D3B8C", "#FFFFFF", "plum-500 link on surface"), ("#F3E9F7", "#2A1636", "rail text on plum-900"),
    ("#C9B5D6", "#2A1636", "rail muted on plum-900"), ("#196B57", "#DDF2EA", "healthy pill"),
    ("#7A5200", "#FBEFD1", "watch pill"), ("#A63A20", "#FBE2DA", "at-risk pill"),
    ("#544D5E", "#ECE9EF", "churned pill"), ("#245F8C", "#FFFFFF", "demand label"),
    ("#196B57", "#FFFFFF", "up delta"), ("#A63A20", "#FFFFFF", "down delta"),
    ("#2A1636", "#F07A5E", "plum on coral (active mark)"), ("#F3E9F7", "#1E0F27", "hero text"),
]


def lum(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


bad = 0
for fg, bg, what in PAIRS:
    a, b = sorted((lum(fg), lum(bg)), reverse=True)
    r = (a + 0.05) / (b + 0.05)
    ok = r >= 4.5
    bad += not ok
    print(f"{'ok ' if ok else 'FAIL'} {r:5.2f}  {what}")
sys.exit(1 if bad else 0)
