from pathlib import Path
p=Path('/mnt/data/work/visual_edit/game/render/world_draw.py')
s=p.read_text()
s=s.replace('        self.draw_sky(cb)\n\n        if self.quality > 0:', '        self.draw_sky(cb)\n        self.draw_biome_backdrop(cb)\n\n        if self.quality > 0:')
s=s.replace('                if r > 0.18:\n                    continue', '                if r > 0.32:\n                    continue')
marker='    def draw_decor(self, x, y, k):\n'
method=r'''    def draw_biome_backdrop(self, cb):
        """Large parallax pixel-art scenery and celestial effects behind gameplay."""
        c = self.canvas
        w, h = self.bw, self.bh
        t = self.time
        # Keep this layer mostly in the upper 60% so bullets and the snake remain readable.
        horizon = h * 0.68
        parx = self.cam_x * CELL
        pary = self.cam_y * CELL
        st = STYLES[cb]
        p = self.pal[cb]

        def poly(points, fill, outline=""):
            c.create_polygon(*points, fill=fill, outline=outline)

        def rect(x1,y1,x2,y2,fill,outline=""):
            c.create_rectangle(x1,y1,x2,y2,fill=fill,outline=outline)

        # Distant layered silhouettes. These are deliberately pixel-ish and low contrast.
        if cb == 0:  # Frost Moon / lunar ruins
            # giant moon/planet inspired by the supplied reference image
            mx, my = w*0.78 - (parx*0.015)%70, h*0.18 - (pary*0.01)%25
            c.create_oval(mx-105,my-105,mx+105,my+105,fill="#172c4c",outline="#5d8fc0",width=2)
            c.create_oval(mx-92,my-96,mx+88,my+90,fill="#24476a",outline="")
            for dx,dy,rr in [(-42,-28,13),(20,-55,9),(52,18,16),(-12,48,8),(-60,35,7)]:
                c.create_oval(mx+dx-rr,my+dy-rr,mx+dx+rr,my+dy+rr,fill="#1b3552",outline="#365d7d")
            # distant frozen ridge and monoliths
            poly([(0,horizon+35),(w*.15,horizon-20),(w*.28,horizon+15),(w*.43,horizon-10),(w*.57,horizon+20),(w*.72,horizon-12),(w*.9,horizon+8),(w,horizon-8),(w,h),(0,h)],"#0d1b30")
            for xx,hh in [(w*.13,75),(w*.31,52),(w*.58,88),(w*.86,62)]:
                rect(xx-7,horizon-hh,xx+7,horizon+16,"#132a46")
                poly([(xx-7,horizon-hh),(xx,horizon-hh-12),(xx+7,horizon-hh),(xx+5,horizon-hh+10),(xx-5,horizon-hh+10)],"#1b3957")
                c.create_line(xx,horizon-hh-12,xx,horizon-5,fill="#4c7192",width=1)
            # constellation: fixed stars connected by thin blue lines
            pts=[(w*.10,h*.22),(w*.18,h*.14),(w*.27,h*.20),(w*.34,h*.11),(w*.44,h*.18),(w*.52,h*.10)]
            for a,b in zip(pts,pts[1:]): c.create_line(*a,*b,fill="#557fa8",width=1)
            for x,y in pts: c.create_oval(x-2,y-2,x+2,y+2,fill="#d9f4ff",outline="")
            # comet / meteor shower
            for i in range(6):
                phase=(t*(0.28+0.03*i)+i*1.7)%1.0
                x=(w*(0.05+i*0.17)+phase*w*0.55)%w
                y=(h*(0.05+i*0.07)+phase*h*0.40)% (h*0.58)
                c.create_line(x-30,y-18,x,y,fill="#8ecbff",width=2)
                c.create_line(x-12,y-7,x,y,fill="#e9f8ff",width=2)
                c.create_oval(x-2,y-2,x+2,y+2,fill="#ffffff",outline="")

        elif cb == 1:  # Misty Lake
            poly([(0,horizon+25),(w*.18,horizon-5),(w*.34,horizon+14),(w*.5,horizon-18),(w*.68,horizon+12),(w*.82,horizon-7),(w,horizon+20),(w,h),(0,h)],"#0b2435")
            # distant snowy pines
            for i in range(11):
                x=(i/10)*w
                base=horizon+20
                hh=28+(i%4)*9
                poly([(x,base-hh),(x-18,base-6),(x-8,base-8),(x-22,base+8),(x+22,base+8),(x+8,base-8),(x+18,base-6)],"#12384d")
            # water reflection bands
            for i in range(7):
                yy=horizon+38+i*17
                c.create_line(w*.05,yy,w*.95,yy,fill="#1c5064",width=2)
                c.create_line(w*.25,yy+5,w*.72,yy+5,fill="#2b6d7f",width=1)

        elif cb == 2:  # Forest of Magic
            # layered canopy creates depth
            for i in range(12):
                x=(i/11)*w
                base=horizon+35
                hh=55+(i%5)*13
                rect(x-5,base-hh*.35,x+5,base,"#1a3321")
                c.create_oval(x-42,base-hh,x+42,base-hh+55,fill="#12331f",outline="#285332")
                c.create_oval(x-25,base-hh+22,x+35,base-hh+70,fill="#174329",outline="")
            # magical mushroom glows
            for x,y,s in [(w*.12,h*.48,1),(w*.38,h*.57,.8),(w*.72,h*.50,1.2),(w*.9,h*.55,.7)]:
                c.create_oval(x-10*s,y-7*s,x+10*s,y+7*s,fill="#6f3f8f",outline="#c58cff")
                rect(x-2*s,y+5*s,x+2*s,y+17*s,"#7c6047")

        elif cb == 3:  # Scarlet Mansion
            # mansion silhouette and ironwork
            rect(w*.17,h*.34,w*.83,horizon+25,"#210d1c",outline="#6d263c")
            poly([(w*.10,h*.36),(w*.25,h*.23),(w*.4,h*.36)],"#2a0c1d",outline="#7d2a42")
            poly([(w*.60,h*.36),(w*.76,h*.20),(w*.9,h*.36)],"#2a0c1d",outline="#7d2a42")
            for x in [w*.25,w*.38,w*.62,w*.75]:
                rect(x-8,h*.42,x+8,h*.62,"#0b0b13",outline="#c44c61")
                c.create_oval(x-4,h*.46,x+4,h*.54,fill="#ffd477",outline="")
            for x in range(int(w*.05),int(w*.96),28):
                c.create_line(x,horizon+12,x,horizon+55,fill="#5d2536",width=2)
                c.create_line(x-8,horizon+18,x,horizon+6,x+8,horizon+18,fill="#7d3348",width=1)

        elif cb == 4:  # Netherworld
            # layered pale hills and ghostly torii-like gates
            poly([(0,horizon+10),(w*.16,horizon-32),(w*.31,horizon+3),(w*.48,horizon-42),(w*.65,horizon+2),(w*.83,horizon-30),(w,horizon+8),(w,h),(0,h)],"#19193a")
            for x in [w*.18,w*.49,w*.79]:
                rect(x-3,h*.34,x+3,horizon+18,"#3c315b")
                rect(x-28,h*.37,x+28,h*.37+5,"#6d5a9a")
                rect(x-20,h*.33,x+20,h*.33+5,"#6d5a9a")
            # sakura canopy
            for x in [w*.08,w*.33,w*.67,w*.91]:
                c.create_line(x,h*.55,x+10,h*.32,fill="#403252",width=4)
                for dx,dy in [(-20,-5),(0,-20),(18,-2),(5,8)]:
                    c.create_oval(x+dx-13,h*.30+dy,x+dx+13,h*.30+dy+25,fill="#4b3d70",outline="#8b7ab8")

        else:  # Hakurei Shrine
            # mountain ridge + shrine gate + paper lanterns
            poly([(0,horizon+18),(w*.18,horizon-36),(w*.33,horizon+8),(w*.5,horizon-55),(w*.7,horizon+2),(w*.86,horizon-38),(w,horizon+12),(w,h),(0,h)],"#241527")
            gx=w*.5
            rect(gx-5,h*.31,gx+5,horizon+28,"#6e2b35")
            rect(gx-105,h*.31,gx+105,h*.31+8,"#9b3e4b")
            rect(gx-82,h*.26,gx+82,h*.26+7,"#b34b57")
            rect(gx-105,h*.34,gx-96,horizon+25,"#7f303b")
            rect(gx+96,h*.34,gx+105,horizon+25,"#7f303b")
            for x in [w*.12,w*.3,w*.7,w*.88]:
                c.create_line(x,h*.38,x,h*.68,fill="#5a2730",width=4)
                c.create_oval(x-8,h*.34,x+8,h*.39,fill="#ffb0c8",outline="#ffdbe7")
            # sakura petals drifting across all shrine foreground
            for i in range(12):
                x=(i*83+t*12*(1+(i%3)*.2))%w
                y=(h*.18+i*31+t*7)%horizon
                c.create_polygon(x,y,x+4,y+2,x+2,y+6,x-2,y+4,fill="#ffb4ca",outline="")

        # Small universal star field and rare meteors for every biome.
        for i in range(16):
            x=(i*137.0 + (parx*0.025))%w
            y=(i*71.0 + (pary*0.012))%(h*.58)
            q=1 if i%3 else 2
            c.create_rectangle(x,y,x+q,y+q,fill="#c9d9ef",outline="")
        if cb != 0 and int(t*0.65)%9 == 0:
            phase=(t*0.55)%1
            x=(w*.92-phase*w*.9)
            y=h*.10+phase*h*.28
            c.create_line(x-28,y-18,x,y,fill="#d5e9ff",width=2)
            c.create_oval(x-2,y-2,x+2,y+2,fill="#ffffff",outline="")

'''
if marker not in s: raise SystemExit('marker missing')
s=s.replace(marker,method+marker)
p.write_text(s)
