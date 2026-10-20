import tkinter as tk, subprocess, os
from game.app import SnakeTerminal
root=tk.Tk(); root.geometry('1366x730+0+0')
app=SnakeTerminal(root)
app.state='tree'; app.tree_tab='passive'; app.tree_zoom=0.55; app.tree_pan=[0,0]
root.update_idletasks(); root.update()
def shot():
    try: subprocess.run(['/opt/imagemagick/bin/import','-window','root','/mnt/data/passive_test.png'],timeout=2,check=False)
    except Exception as e: print('shot',e)
    root.destroy()
root.after(700, shot)
root.mainloop()
print('done')
