import tkinter as tk,time
from game.app import SnakeTerminal
SnakeTerminal.animate=lambda self: None
root=tk.Tk(); root.geometry('1366x730+0+0')
app=SnakeTerminal(root); app.state='tree'; app.tree_tab='skill'; app.tree_zoom=.68
root.update();
# initial render
s=time.perf_counter(); app.draw_tree(); root.update(); t0=time.perf_counter()-s
# cached renders
s=time.perf_counter()
for _ in range(120): app.draw_tree(); root.update_idletasks()
t=time.perf_counter()-s
# hover movement across 50 positions, forcing static refresh
s=time.perf_counter()
for i in range(50):
    app.mouse=(350+i*8,250)
    app.draw_tree(); root.update_idletasks()
h=time.perf_counter()-s
print('initial',t0,'cached120',t,'per',t/120,'hover50',h,'per',h/50,'nodes',len(app.skill_hits))
root.destroy()
