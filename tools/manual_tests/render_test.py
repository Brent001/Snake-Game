import tkinter as tk
from game.app import SnakeTerminal
SnakeTerminal.animate=lambda self: None
root=tk.Tk(); root.geometry('1366x730+0+0')
app=SnakeTerminal(root); app.state='tree'; app.tree_tab='passive'; app.tree_zoom=.55; app.draw_tree(); root.update()
try:
    app.canvas.postscript(file='/mnt/data/passive_tree.eps', colormode='color')
    print('EPS OK')
except Exception as e: print('EPS ERR',repr(e))
app.tree_tab='skill'; app.tree_zoom=.72; app.draw_tree(); root.update()
try:
    app.canvas.postscript(file='/mnt/data/skill_tree.eps', colormode='color')
    print('skill EPS OK')
except Exception as e: print('skill EPS ERR',repr(e))
root.destroy()
