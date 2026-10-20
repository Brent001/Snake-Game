import tkinter as tk
from game.app import SnakeTerminal
root=tk.Tk(); root.geometry('1366x730+0+0')
app=SnakeTerminal(root)
app.state='tree'; app.tree_tab='passive'; app.tree_zoom=0.55; app.tree_pan=[0,0]
root.update(); app.draw_tree(); root.update(); root.after(100, root.quit); root.mainloop()
root.update()
root.wm_geometry('1366x730')
try: root.postscript(file='/mnt/data/v39_passive.ps', colormode='color')
except Exception: pass
root.destroy()
