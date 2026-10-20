"""8-bit pixel sprites (character grids + palettes) and the run-length compiler."""

SPR = {
    "reimu": ([
        "....RR....RR....", "...RRRRRRRRRR...", "...KKKKKKKKKK...", "..KKSSSSSSSSKK..",
        "..KRSeSSSSeSRK..", "..KKSSSSSSSSKK..", "...KSSSSSSSSK...", "....YYYYYYYY....",
        "..WWRRRRRRRRWW..", ".SWWRRWWWWRRWWS.", "..WWRRRRRRRRWW..", "....RRRRRRRR....",
        "...RRRRRRRRRR...", "..RRRRRRRRRRRR..", "....WW....WW....", "...KKK....KKK..."],
        dict(R="#e0243c", K="#1a1420", S="#ffd9b8", e="#8a1020", Y="#ffd34d", W="#ffffff")),
    "cirno": ([
        "......NNNN......", "...BBBBNNBBBB...", "..BBBBBBBBBBBB..", "..BBSSSSSSSSBB..",
        "..BBSeSSSSeSBB..", "..BBSSSSSSSSBB..", "...BBSSSSSSBB...", "..I..WWRRWW..I..",
        ".III.WWWWWW.III.", "III.NNNNNNNN.III", ".II.NNNNNNNN.II.", "..I.NNNNNNNN.I..",
        "....NNNNNNNN....", "...NNNNNNNNNN...", "....SS....SS....", "....WW....WW...."],
        dict(N="#2f6bd6", B="#8fc8ff", S="#ffd9b8", e="#2040a0", I="#bff4ff", W="#ffffff", R="#e03040")),
    "marisa": ([
        ".......KK.......", "......KKKK......", ".....KKKKKK.....", "....KKWWWWKK....",
        ".KKKKKKKKKKKKKK.", "..YYSSSSSSSSYY..", "..YYSeSSSSeSYY..", "..YYSSSSSSSSYY..",
        "...YY.SSSS.YY...", "..SKKWWWWWWKKS..", "...KKWWWWWWKK...", "...KKWWWWWWKK...",
        "..KKKKKKKKKKKK..", ".KKKKKKKKKKKKKK.", "....SS....SS....", "....KK....KK...."],
        dict(K="#2a2038", W="#ffffff", Y="#ffd34d", S="#ffd9b8", e="#c08000")),
    "sakuya": ([
        "................", "....WWWWWWWW....", "...LLLLLLLLLL...", "..LLLLLLLLLLLL..",
        "..LLSSSSSSSSLL..", "..LLSeSSSSeSLL..", "..LLSSSSSSSSLL..", "..LL.SSSSSS.LL..",
        "....BBBBBBBB....", "..WWNNWWWWNNWW..", ".SWWNNWWWWNNWWS.", "..WNNNWWWWNNNW..",
        "...NNNNNNNNNN...", "..NNNNNNNNNNNN..", "..WWWWWWWWWWWW..", "....SS....SS...."],
        dict(L="#dfe6f2", W="#ffffff", N="#2a4a9a", B="#4a6ad0", S="#ffd9b8", e="#2a4aff")),
    "youmu": ([
        "....KKKKKKKK....", "...LLLLLLLLLL...", "..LLLLLLLLLLLL..", "..LLSSSSSSSSLL..",
        "..LLSeSSSSeSLL..", "..LLSSSSSSSSLL..", "...LL.SSSS.LL...", "....GGGGGGGG....",
        "..WWGGGGGGGGWW..", ".SWWGGWWWWGGWWS.", "..WWGGWWWWGGWW..", "....GGGGGGGG....",
        "...GGGGGGGGGG...", "..GGGGGGGGGGGG..", "....SS....SS....", "....KK....KK...."],
        dict(K="#14101e", L="#dfe6f2", G="#2f9d5a", W="#ffffff", S="#ffd9b8", e="#2a7a4a")),
    # ---- enemies (12 x 12)
    "rabbit": ([
        "..WW....WW..", "..WW....WW..", "..WW....WW..", "..WWWWWWWW..", ".WWWWWWWWWW.", ".WWRWWWWRWW.",
        ".WWWWWWWWWW.", ".WWWWPPWWWW.", "..WWWWWWWW..", "..WWWWWWWW..", "..WW....WW..", "..GG....GG.."],
        dict(W="#ffffff", R="#ff3050", P="#ffa0b8", G="#c8d0e0")),
    "fairy": ([
        "....BBBB....", "...BBBBBB...", "..BBSSSSBB..", "..BSeSSeSB..", "I.BBSSSSBB.I", "II..NNNN..II",
        "II.NNNNNN.II", ".I.NNNNNN.I.", "....NNNN....", "....SSSS....", "....S..S....", "............"],
        dict(B="#8fc8ff", S="#ffd9b8", e="#2040a0", I="#bff4ff", N="#2f6bd6")),
    "kodama": ([
        "....RRRR....", "..RRWWRRRR..", ".RRRWWRRWRR.", ".RWRRRRRRRR.", "RRRRRRRRRRRR", "..SSSSSSSS..",
        "..SeSSSSeS..", "..SSSSSSSS..", "..SSSSSSSS..", "...SS..SS...", "..GG....GG..", "............"],
        dict(R="#d84a4a", W="#ffffff", S="#e8e0c8", e="#202020", G="#6a8a4a")),
    "maid": ([
        "....RRRR....", "...RRRRRR...", "..RRSSSSRR..", "..RSeSSeSR..", "..RRSSSSRR..", "...DWWWWD...",
        "..DDWWWWDD..", "..DDDWWDDD..", ".DDDDDDDDDD.", ".DDDDDDDDDD.", "...SS..SS...", "...SS..SS..."],
        dict(R="#e8503a", S="#ffd9b8", e="#802010", D="#a01828", W="#ffffff")),
    "phantom": ([
        "....WWWW....", "...WWWWWW...", "..WWWWWWWW..", "..WKKWWKKW..", "..WKKWWKKW..", "..WWWWWWWW..",
        "..WWWKKWWW..", "..WWWWWWWW..", ".WWWWWWWWWW.", ".WWW.WW.WWW.", "..W...W...W.", "............"],
        dict(W="#bcd8ff", K="#1b1b3a")),
    "komainu": ([
        "..R......R..", ".RRR....RRR.", ".RRRRRRRRRR.", ".RGGGGGGGGR.", ".GGWGGGGWGG.", ".GGGGGGGGGG.",
        "..GGGGGGGG..", "..GGGPPGGG..", "..GGGGGGGG..", ".GGGGGGGGGG.", ".GG.GGGG.GG.", ".KK......KK."],
        dict(R="#c83030", G="#a8a8b8", W="#ffffff", P="#505060", K="#383848")),
    "star": ([
        ".....YY.....", ".....YY.....", "....YYYY....", "YYYYYYYYYYYY", ".YYYeYYeYYY.", "..YYYYYYYY..",
        "...YYYYYY...", "..YYYYYYYY..", "..YYY..YYY..", ".YY......YY.", "............", "............"],
        dict(Y="#ffe55a", e="#7a5a00")),
    "wisp": ([
        ".....BB.....", "....BBBB....", "...BBBBBB...", "..BBWBBWBB..", "..BBBBBBBB..", ".BBBBBBBBBB.",
        ".BBBBBBBBBB.", ".BBBBBBBBBB.", "..BBBBBBBB..", "...BB..BB...", "....B..B....", "............"],
        dict(B="#4aa8ff", W="#ffffff")),
    "shroom": ([
        "...RRRRRR...", "..RRWRRRWR..", ".RRRRRRWRRR.", ".RWRRRRRRRR.", "RRRRRRRRRRRR", "..SSSSSSSS..",
        "..SeSSSSeS..", "..SSSSSSSS..", "...SSSSSS...", "...SS..SS...", "..SS....SS..", "............"],
        dict(R="#a04ad8", W="#ffe9a0", S="#e8e0c8", e="#202020")),
    "bat": ([
        "............", "K....KK....K", "KK..KKKK..KK", "KKKKKKKKKKKK", "KKKKRKKRKKKK", ".KKKKKKKKKK.",
        "..KKWKKWKK..", "...KKKKKK...", "....K..K....", "............", "............", "............"],
        dict(K="#7a2a5a", R="#ff3050", W="#ffffff")),
    "lantern": ([
        "....GGGG....", "...GGGGGG...", "....KKKK....", "...KYYYYK...", "..KKYYWYKK..", "..KKYYYYKK..",
        "..KKYYYYKK..", "...KYYYYK...", "....KKKK....", "....GGGG....", "...G.GG.G...", "............"],
        dict(G="#8a6ad0", K="#2a2050", Y="#9fd8ff", W="#ffffff")),
    "fox": ([
        "..R......R..", ".RRR....RRR.", ".RRRRRRRRRR.", ".RWWRRRRWWR.", ".RWeRRRReWR.", ".RRRRKKRRRR.",
        "..RRRWWRRR..", "...RRRRRR...", "..RRRRRRRR..", ".RRR.RR.RRR.", ".RW..RR..WR.", "............"],
        dict(R="#ff9a5a", W="#ffffff", e="#401010", K="#401010")),

    # ---- added enemy silhouettes, still compiled as the same crisp 8-bit 12x12 style
    "kappa": ([
        "....GGGG....", "...GGGGGG...", "..GSSSSSSG..", "..GSSeSSSG..", ".GGSSSSSSGG.", ".GGWWWWWWGG.", "..GGGKKGGG..", "..GGKKKKGG..", "...GGGGGG...", "..GG....GG..", ".GG......GG.", "............"],
        dict(G="#55c7a1", S="#ffd9b8", e="#2a6f59", W="#e9fff7", K="#173b34")),
    "doll": ([
        "....PPPP....", "...PPPPPP...", "..PSSSSSSP..", "..PSeSSSeP..", ".PPSSSSSSPP.", "...PPWWPP...", "..PPWWWWPP..", "..PPWWWWPP..", "...PPPPPP...", "..PP....PP..", "..PP....PP..", "............"],
        dict(P="#b77dff", S="#ffd9b8", e="#4f2a75", W="#f6efff")),
    "maid_blue": ([
        "....BBBB....", "...BBBBBB...", "..BSSSSSSB..", "..BSeSSeSB..", "..BBSSSSBB..", "...DWWWWD...", "..DDWWWWDD..", "..DDDWWDDD..", ".DDDDDDDDDD.", ".DDDDDDDDDD.", "...SS..SS...", "...SS..SS..."],
        dict(B="#8da9ff", S="#ffd9b8", e="#314a9c", D="#425a9f", W="#ffffff")),
    "wraith": ([
        "...PPPP...", "..PPPPPP..", ".PPPPPPPP.", ".PPKKPPPP.", ".PPPPPPPP.", "..PPPPPP..", "...PPPP...", "..PPKKPP..", ".PPPPPPPP.", "...P..P...", "............", "............"],
        dict(P="#9b72e8", K="#241941")),
    "umbrella": ([
        "...RRRR...", "..RRRRRR..", ".RRRRRRRR.", "RRRWWWWRRR", "RRWWWWWWRR", "..WSSSSW..", "..WSeSeW..", "...SSSS...", "....SS....", "...SS.SS..", "...SS.SS..", "............"],
        dict(R="#d94b8d", W="#fff0fb", S="#ffd9b8", e="#6b1b48")),

    # ---- pickups / menu art
    "food": ([
        ".......GG...", "......GG....", "...RRRGRRR..", "..RRWRRRRRR.", ".RRWRRRRRRRR", ".RRRRRRRRRRR",
        ".RRRRRRRRRRR", ".RRRRRRRRRDR", "..RRRRRRRDR.", "..RRRRRRDD..", "...RRRRDD...", ".....DD....."],
        dict(R="#ff4d6d", W="#ffd0d8", G="#5dffb0", D="#b01838")),
    "food_gold": ([
        ".......GG...", "......GG....", "...YYYGYYY..", "..YYWYYYYYY.", ".YYWYYYYYYYY", ".YYYYYYYYYYY",
        ".YYYYYYYYYYY", ".YYYYYYYYYDY", "..YYYYYYYDY.", "..YYYYYYDD..", "...YYYYDD...", ".....DD....."],
        dict(Y="#ffd34d", W="#fff6c8", G="#5dffb0", D="#a8741a")),
    "snake_head": ([
        "....KKKK....", "..KKGGGGKK..", ".KGGGHHGGGK.", ".KGGHHHHGGK.", "KGGGGGGGGGGK", "KGEEGGGGEEGK",
        "KGEKGGGGKEGK", "KGGGGGGGGGGK", ".KGGGKKGGGK.", ".KGGGGGGGGK.", "..KKGGGGKK..", "....KRRK...."],
        dict(K="#0a0a14", G="#ffd34d", H="#fff1c2", E="#ffffff", R="#ff3050")),
}


def sprite_runs(rows, pal):
    """Compile a sprite grid into horizontal runs (x, y, width, colour) for fast drawing."""
    n = len(rows[0])
    runs = []
    for y, row in enumerate(rows):
        row = row.ljust(n, ".")[:n]
        x = 0
        while x < n:
            ch = row[x]
            if ch == ".":
                x += 1
                continue
            x2 = x
            while x2 + 1 < n and row[x2 + 1] == ch:
                x2 += 1
            runs.append((x, y, x2 - x + 1, pal[ch]))
            x = x2 + 1
    return runs, n


SPRITE_RUNS = {k: sprite_runs(*v) for k, v in SPR.items()}
