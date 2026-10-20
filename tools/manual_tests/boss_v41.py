import sys, tkinter as tk, math
sys.path.insert(0,'.')
from game.app import SnakeTerminal
from game.data.bosses import BOSSES
from game.world.layout import ARENAS

root=tk.Tk(); root.geometry('1366x730+0+0'); root.withdraw()
app=SnakeTerminal(root); app.animate=lambda: None
app.state='playing'; app.ammo=9; app.aim_ok=False
for cid in ('viper','python','cobra','mamba'):
    app.run_class=cid
    for bi in range(len(BOSSES)):
        app.reset_game(); app.state='playing'; app.ammo=9
        a=ARENAS[bi]
        # a small snake placed low in the arena to exercise aiming + movement
        app.snake=[(int(a['mx']), int(a['y2']-4)), (int(a['mx']), int(a['y2']-5)), (int(a['mx']), int(a['y2']-6))]
        app.prev=list(app.snake)
        app.start_boss(bi)
        app.boss['state']='fight'; app.boss['t']=0.0; app.boss['timer']=0.0
        app.skills_phase_start(); app.boss['hp']=BOSSES[bi]['phases'][0]['hp']
        max_bullets=0
        for _ in range(900):
            app.update_boss(1/60)
            app.update_bullets(1/60)
            max_bullets=max(max_bullets,len(app.bullets))
            if app.boss.get('state') != 'fight': break
        # Validate finite, bounded boss coordinates and active attacks were produced.
        bx,by=app.boss['x'],app.boss['y']
        assert math.isfinite(bx) and math.isfinite(by)
        assert a['x1']-0.01 <= bx <= a['x2']+0.01
        assert a['y1']-0.01 <= by <= a['y2']+0.01
        assert max_bullets > 0, (cid, BOSSES[bi]['name'])
        print('BOSS_OK',cid,BOSSES[bi]['name'],'max_bullets',max_bullets,'pos',round(bx,2),round(by,2))
root.destroy()
