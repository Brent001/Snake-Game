import tkinter as tk
from game.app import SnakeTerminal
root=tk.Tk(); root.geometry('1366x730+0+0')
app=SnakeTerminal(root)
app.state='tree'; app.tree_tab='passive'; app.tree_zoom=0.55; app.tree_pan=[0,0]
root.after(1000, root.quit)
root.mainloop()
print('exited')
