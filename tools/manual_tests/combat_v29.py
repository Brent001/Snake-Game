import tkinter as tk, sys
sys.path.insert(0,'.')
from game.app import SnakeTerminal
from game.data.active_skill_tree import SKILL_NODES
from game.data.skills import SKILLS

root=tk.Tk(); root.geometry('1366x730+0+0')
app=SnakeTerminal(root); app.animate=lambda: None
app.state='playing'; app.ammo=9; app.aim_ok=False
for cid in ('viper','python','cobra','mamba'):
    app.run_class=cid
    app.reset_game()
    app.state='playing'; app.ammo=9
    app.skill_alloc=set()
    # root free nodes + a representative deep set from every skill
    for key, *_ in SKILLS:
        rootid=f'{cid}:{key}:root'
        app.skill_alloc.add(rootid)
        for nid in (f'{cid}:{key}:p0_1',f'{cid}:{key}:p0_2',f'{cid}:{key}:p0_4',f'{cid}:{key}:p0_6'):
            if nid in SKILL_NODES: app.skill_alloc.add(nid)
    app.skill_pts=999
    app.recompute()
    # direct calls for representative skills
    for fn in (app.dash, app.primary_attack, app.coil, app.shed, app.heat_sense, app.tongue, app.spit, app.rattle, app.camo, app.volley, app.bulwark, app.class_skill):
        try: fn()
        except Exception as e:
            raise RuntimeError(f'{cid} {fn.__name__}: {e}') from e
    app.update_shots(0.02)
    app.root.update_idletasks()
    print('COMBAT_OK', cid, 'shots',len(app.shots),'effects',len(app.effects))
root.destroy()
