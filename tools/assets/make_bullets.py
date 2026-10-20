import colorsys, json, math, os
from PIL import Image
SRC='rars/Danmaku/Danmaku/Shot_01.png'; OUT='game_src/game/assets/bullets'; os.makedirs(OUT,exist_ok=True)
im=Image.open(SRC).convert('RGBA')
SIZES=(14,18,22,30)
NC=18
def left(row,col): return im.crop((col*16,row*16,col*16+16,row*16+16))
def right(row,col): return im.crop((576+col*32,row*32,576+col*32+32,row*32+32))
# kind -> (getter(col, frame), directional, frames)
KINDS={
 'orb':(lambda c,f:right(0,c),False,1),
 'star':(lambda c,f:left(10,c),False,1),
 'bfly':(lambda c,f:right(8+f,c),False,2),
 'rice':(lambda c,f:left(3,c),True,1),
 'amulet':(lambda c,f:left(4,c),True,1),
 'knife':(lambda c,f:left(5,c),True,1),
 'ice':(lambda c,f:left(9,c),True,1),
}
# column hues (from the red..yellow ring colours of each column of the sheet)
hues=[]
for c in range(NC):
    px=[p for p in right(0,c).getdata() if p[3]>200]
    best=max(px,key=lambda p:colorsys.rgb_to_hsv(p[0]/255,p[1]/255,p[2]/255)[1]*colorsys.rgb_to_hsv(p[0]/255,p[1]/255,p[2]/255)[2])
    h,s,v=colorsys.rgb_to_hsv(*(x/255 for x in best[:3])); hues.append(round(h,4))
json.dump(hues,open(f'{OUT}/hues.json','w'))
print(hues)
for kind,(get,dirn,frames) in KINDS.items():
    for size in SIZES:
        cell=math.ceil(size*1.45) if dirn else size
        rows=16 if dirn else frames
        sheet=Image.new('RGBA',(NC*cell,rows*cell),(0,0,0,0))
        for c in range(NC):
            for r in range(rows):
                f=0 if dirn else r
                spr=get(c,f).resize((size,size),Image.LANCZOS if size>=16 else Image.NEAREST)
                if dirn:
                    theta=r*360/16                      # screen-space clockwise degrees from +x
                    spr=spr.rotate(-(theta+90),resample=Image.BICUBIC,expand=True)
                tile=Image.new('RGBA',(cell,cell),(0,0,0,0)); tile.alpha_composite(spr,((cell-spr.width)//2,(cell-spr.height)//2))
                sheet.alpha_composite(tile,(c*cell,r*cell))
        sheet.quantize(colors=192,method=Image.FASTOCTREE).save(f'{OUT}/{kind}_{size}.png',optimize=True)
tot=sum(os.path.getsize(f'{OUT}/{f}') for f in os.listdir(OUT)); print(tot//1024,'KB')
