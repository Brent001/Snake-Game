"""Entry point - run with:  python main.py

The world is generated (about a second of pure-Python work) on a background thread while the window is already
open, so the app never looks frozen on start-up.  All Tk calls stay on the main thread (tkinter is not thread-safe).
"""
import atexit
import gc
import os
import sys
import threading
import tkinter as tk


def tune_process():
    """Windows hands out timer ticks of ~15.6 ms by default, so Tk's after(16) really fires every 15.6 ms or 31 ms and
    the game ran at 30-60 fps even when the machine was idle.  Ask for 1 ms ticks and a slightly higher priority."""
    if sys.platform != "win32":
        return
    try:
        import ctypes
        winmm = ctypes.windll.winmm
        winmm.timeBeginPeriod(1)
        atexit.register(lambda: winmm.timeEndPeriod(1))
    except Exception:
        pass
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.SetPriorityClass(k32.GetCurrentProcess(), 0x00008000)      # ABOVE_NORMAL_PRIORITY_CLASS
    except Exception:
        pass


def main():
    tune_process()
    # GPU VFX is opt-in when requested explicitly; otherwise the game auto-enables it when the
    # optional dependencies are installed.  Use `python main.py --cpu` to force the legacy renderer.
    if "--cpu" in sys.argv:
        os.environ["REPAIR_GPU"] = "off"
    elif "--gpu" in sys.argv:
        os.environ["REPAIR_GPU"] = "on"
    window = tk.Tk()
    window.title("Repair Terminal")
    window.configure(bg="#080e1c")
    window.geometry("960x600")
    status = tk.Label(window, text="GENERATING WORLD ...", font=("Consolas", 16, "bold"), fg="#7df9ff", bg="#080e1c")
    status.pack(expand=True)
    box = {}

    def load():
        try:
            from game.app import SnakeTerminal      # importing builds the whole procedural map
            box["cls"] = SnakeTerminal
        except BaseException as exc:                # re-raised on the main thread below
            box["err"] = exc

    worker = threading.Thread(target=load, name="world-gen", daemon=True)
    worker.start()

    def poll():
        if worker.is_alive():
            window.after(30, poll)
            return
        if "err" in box:
            window.destroy()
            raise box["err"]
        status.destroy()
        # The generated world is millions of long-lived objects: park them outside the cyclic GC (so its collections
        # stop re-scanning them mid-fight) and collect the young generations less often.
        gc.collect()
        gc.freeze()
        gc.set_threshold(5000, 20, 20)
        box["cls"](window)

    poll()
    window.mainloop()


if __name__ == "__main__":
    main()
