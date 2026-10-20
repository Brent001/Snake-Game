import tkinter as tk
from game.app import SnakeTerminal
SnakeTerminal.animate = lambda self: None
from game.data.skills import SKILLS

root=tk.Tk(); root.geometry('1366x730+0+0')
app=SnakeTerminal(root)
app.state='tree'
app.tree_tab='passive'; app.tree_zoom=0.55; app.tree_pan=[0,0]
root.update_idletasks(); root.update(); app.draw_tree(); root.update()
assert len(app.class_tree_ids()) == 175
assert len(app.tree_control_rects) >= 2
# click H-like sidebar control through direct controller and verify width change
before=app._tree_side_width(); app.tree_control('sidebar'); assert app._tree_side_width() == 48
app.tree_control('sidebar'); assert app._tree_side_width() == before
# skill overview
app.tree_tab='skill'; app.tree_zoom=0.72; app.tree_pan=[0,0]
app.draw_tree(); root.update()
assert len(app.skill_hits) == 336
assert len(app.skill_lines()) == len(SKILLS) == 12
# verify a path node allocates
rootid='viper:dash:root'; assert rootid in app.skill_alloc
# pick first spendable dash node connected to root
nid='viper:dash:p0_0'
assert app.can_skill_alloc(nid); old=app.skill_pts; app.skill_alloc.add(nid); app.skill_pts-=1; app.recompute(); assert app.skill_pts == old-1
# refund
assert app.can_skill_refund(nid); app.skill_alloc.remove(nid); app.skill_pts+=1; app.recompute(); assert app.skill_pts==old
# render every tree tab once
for tab in ('passive','skill'):
    app.tree_tab=tab; app.draw_tree(); root.update()
root.after(50, root.destroy); root.mainloop()
print('UI smoke OK')
