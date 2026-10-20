"""Biome styles: names, particle settings, terrain density and day/night palettes."""
from ..utils import same

STYLES = [
    dict(name="THE FROST MOON", sub="- Lunar Space -", tcol="#9fd0ff", pcol="#cfe8ff",
        pv=(6, 22), ps=2, wd=0.9, blob=0.1, ln=(4, 10),
        pal=dict(floor=same("#0b1426"), grid=same("#0f1b33"), wall=same("#0c2040"),
            edge=same("#3d95ff"), glow=same("#123a72"), deco=same("#1b3358"), deco2=same("#2a4f86"))),
    dict(name="MISTY LAKE", sub="- Realm of the Ice Fairy -", tcol="#7df9ff", pcol="#e8fbff",
        pv=(-10, 30), ps=3, wd=0.9, blob=0.45, ln=(3, 7),
        pal=dict(floor=("#091c33", "#3e8fb0"), grid=("#0d2a48", "#3683a3"), wall=("#10405e", "#9fdcf0"),
            edge=("#6fe3ff", "#ffffff"), glow=("#13607f", "#4e9dba"), deco=("#1c4e72", "#8fd0e8"), deco2=("#4fa8d0", "#d6f6ff"))),
    dict(name="FOREST OF MAGIC", sub="- Where the Mushrooms Whisper -", tcol="#b8ff8a", pcol="#d8ff70",
        pv=(8, -4), ps=3, wd=1.0, blob=0.5, ln=(3, 8),
        pal=dict(floor=("#0a1a12", "#2f7a46"), grid=("#102418", "#286b3c"), wall=("#12301c", "#1d5a30"),
            edge=("#58d68d", "#9cff9c"), glow=("#1c5a34", "#134523"), deco=("#1f4a2c", "#d85a5a"), deco2=("#7a3aa8", "#ffe9a0"))),
    dict(name="SCARLET MANSION GROUNDS", sub="- Crimson Halls -", tcol="#ff8aa0", pcol="#ff7a5a",
        pv=(0, -26), ps=2, wd=1.0, blob=0.1, ln=(6, 16),
        pal=dict(floor=("#1a0a14", "#6a2a3a"), grid=("#2a0f1f", "#5a2030"), wall=("#3a0f22", "#7a2438"),
            edge=("#ff4f6d", "#ff9aa8"), glow=("#7a1a2e", "#a03048"), deco=("#3a1428", "#8a3a50"), deco2=("#ffcf5a", "#ffe08a"))),
    dict(name="THE NETHERWORLD", sub="- Realm of the Departed -", tcol="#c9b0ff", pcol="#b8d8ff",
        pv=(5, -12), ps=3, wd=0.7, blob=0.3, ln=(4, 9),
        pal=dict(floor=("#10102a", "#4a4a8a"), grid=("#181838", "#42427c"), wall=("#241f4a", "#5a4f9a"),
            edge=("#b89bff", "#e4d4ff"), glow=("#3d2f7a", "#6a5aaa"), deco=("#2a2a5a", "#8a8ad0"), deco2=("#9fd8ff", "#f0f6ff"))),
    dict(name="HAKUREI SHRINE", sub="- Border of Paradise -", tcol="#ffb3d1", pcol="#ffb3d1",
        pv=(-14, 18), ps=3, wd=0.6, blob=0.25, ln=(3, 6),
        pal=dict(floor=("#1a0f1c", "#8a4a62"), grid=("#25142a", "#7c3f56"), wall=("#3a1830", "#c0607c"),
            edge=("#ff9ac8", "#ffd0e0"), glow=("#7a2a5a", "#a04a66"), deco=("#4a2a40", "#c07a92"), deco2=("#ff8ab8", "#fff0f5"))),
]
