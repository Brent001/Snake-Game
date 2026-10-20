"""Optional OpenGL 3.3+ VFX compositor for Repair Terminal.

This is a GPU *effects* pipeline, not yet a replacement for the complete Tk world renderer.
Tk remains responsible for the CPU/UI layer while this module renders expensive-looking combat
VFX in a transparent, click-through pyglet overlay using ModernGL:

  simulation -> instance buffer -> HDR-ish effect FBO -> separable blur -> transparent composite

The separation lets the current game keep its mature Tk gameplay/UI code while expensive bloom,
particles and rings move to the GPU. When pyglet/ModernGL are unavailable the game falls back to
the existing CPU VFX renderer.
"""
from __future__ import annotations

import atexit
import gc
import math
import os
import platform
import threading
import time
from array import array


GPU_ENV = os.environ.get("REPAIR_GPU", "auto").strip().lower()


def gpu_dependencies_available() -> bool:
    try:
        import pyglet  # noqa: F401
        import moderngl  # noqa: F401
        return True
    except Exception:
        return False


def _harden_pyglet_finalizers():
    """pyglet's BufferObject / ShaderProgram `__del__` call glDelete* and only swallow AttributeError/ImportError.
    Once the GL context is gone (window closed, interpreter exiting) wgl cannot resolve the entry points any more and
    the garbage collector prints "MissingFunctionException: glDeleteBuffers is not exported ...".  The objects die with
    the context anyway, so a failing delete is simply ignored."""
    try:
        from pyglet.graphics import shader, vertexbuffer
    except Exception:
        return
    for cls in (getattr(vertexbuffer, "BufferObject", None), getattr(shader, "ShaderProgram", None),
                getattr(shader, "ComputeShaderProgram", None), getattr(shader, "Shader", None)):
        orig = getattr(cls, "__del__", None) if cls is not None else None
        if orig is None or getattr(orig, "_repair_safe", False):
            continue

        def safe_del(self, _orig=orig):
            try:
                _orig(self)
            except BaseException:
                pass
        safe_del._repair_safe = True
        try:
            cls.__del__ = safe_del
        except Exception:
            pass


class GpuVfxOverlay:
    """Windows-first transparent overlay with a ModernGL post-processing chain."""

    def __init__(self, parent_hwnd: int | None = None):
        self.parent_hwnd = int(parent_hwnd or 0)
        self._lock = threading.Lock()
        self._snapshot = None
        self._geometry = (100, 100, 960, 600, False)
        self._running = False
        self._ready = threading.Event()
        self._failed = ""
        self._thread = None
        self._stop = False
        self._window = None
        self._renderer = None

    @property
    def available(self) -> bool:
        return self._running and self._ready.is_set() and not self._failed

    @property
    def failure(self) -> str:
        return self._failed

    def start(self):
        if GPU_ENV in ("0", "off", "false", "cpu"):
            self._failed = "disabled"
            return False
        if platform.system().lower() != "windows":
            # The overlay positioning / click-through semantics here are deliberately Windows-first.
            self._failed = "GPU overlay currently requires Windows"
            return False
        if not gpu_dependencies_available():
            self._failed = "install pyglet + moderngl to enable GPU VFX"
            return False
        if self._running:
            return True
        _harden_pyglet_finalizers()
        atexit.register(self.stop)
        self._running = True
        self._thread = threading.Thread(target=self._thread_main, name="repair-gpu-vfx", daemon=True)
        self._thread.start()
        self._ready.wait(timeout=6.0)
        return self.available

    def stop(self):
        """Ask the GL thread to tear everything down (with its context current) and wait for it, so nothing is left
        for the garbage collector to delete after the context has gone."""
        self._stop = True
        t = self._thread
        if t is not None and t.is_alive() and t is not threading.current_thread():
            t.join(timeout=2.0)
        self._running = False

    def set_geometry(self, x: int, y: int, w: int, h: int, visible: bool):
        with self._lock:
            self._geometry = (int(x), int(y), max(1, int(w)), max(1, int(h)), bool(visible))

    def submit(self, snapshot: dict):
        if not self.available:
            return
        # Shallow copy the lists to avoid touching the game state from the GL thread.
        # The game builds fresh dicts every frame and never touches them again, so handing over the lists is safe
        # (copying ~700 dicts per frame on the Tk thread was pure overhead).
        with self._lock:
            self._snapshot = snapshot

    # ------------------------------------------------------------------ GPU thread
    def _thread_main(self):
        try:
            import pyglet
            pyglet.options["shadow_window"] = False
            pyglet.options["vsync"] = False
            from pyglet import gl

            config = gl.Config(
                major_version=3,
                minor_version=3,
                alpha_size=8,
                depth_size=0,
                double_buffer=True,
                forward_compatible=False,
            )
            win = pyglet.window.Window(
                width=320,
                height=240,
                visible=False,
                resizable=False,
                caption="Repair Terminal GPU FX",
                style=pyglet.window.Window.WINDOW_STYLE_OVERLAY,
                config=config,
                vsync=False,
            )
            self._window = win
            try:
                win.set_mouse_passthrough(True)
            except Exception:
                pass
            self._renderer = _GpuRenderer(win)
            self._ready.set()
            win.set_visible(False)

            @win.event
            def on_draw():
                self._renderer.draw(self._get_snapshot(), self._get_geometry())

            last_pos = [None, None]

            def tick(_dt):
                if self._stop:
                    pyglet.app.exit()           # _teardown() frees the GL objects and closes the window afterwards
                    return
                try:
                    x, y, w, h, visible = self._get_geometry()
                    if (w, h) != win.get_size():
                        win.set_size(w, h)
                    if visible and not win.visible:
                        win.set_visible(True)
                    elif not visible and win.visible:
                        win.set_visible(False)
                    if visible and [x, y] != last_pos:          # SetWindowPos 120x/s for an unchanged position is waste
                        last_pos[:] = [x, y]
                        try:
                            win.set_location(x, y)
                        except Exception:
                            pass
                except Exception as exc:
                    self._failed = f"overlay update failed: {exc}"

            pyglet.clock.schedule_interval(tick, 1.0 / 120.0)
            pyglet.app.run()
        except Exception as exc:
            self._failed = f"GPU pipeline unavailable: {type(exc).__name__}: {exc}"
            self._ready.set()
        finally:
            self._running = False
            self._teardown()

    def _teardown(self):
        """Free every GL object while the context is still alive and current (runs on the GL thread)."""
        win, rend = self._window, getattr(self, "_renderer", None)
        self._renderer = None
        try:
            if win is not None:
                win.switch_to()
        except Exception:
            pass
        if rend is not None:
            try:
                rend.release()
            except Exception:
                pass
        del rend
        gc.collect()                    # pyglet buffers / shader programs are deleted here, context still current
        try:
            if win is not None:
                win.close()
        except Exception:
            pass
        self._window = None
        gc.collect()

    def _get_snapshot(self):
        with self._lock:
            return self._snapshot or {"particles": [], "rings": [], "flash": 0.0, "flash_power": 0.0, "time": 0.0}

    def _get_geometry(self):
        with self._lock:
            return self._geometry


class _GpuRenderer:
    """Modern OpenGL renderer with particle instancing and a two-pass blur."""

    def __init__(self, window):
        import moderngl
        self.mgl = moderngl
        self.window = window
        self.ctx = moderngl.create_context(require=330)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = (moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA)
        self.time0 = time.perf_counter()
        self.size = (1, 1)
        self._make_programs()
        self._make_buffers()
        self._make_targets(320, 240)

    def release(self):
        """Release every moderngl object explicitly (GL context must be current)."""
        names = ("scene_tex", "blur_a", "blur_b", "scene_fbo", "blur_fbo_a", "blur_fbo_b", "quad_vbo", "inst_vbo",
                 "ring_vbo", "particle_vao", "ring_vao", "post_vao", "post_comp_vao", "flash_vao", "particle_prog",
                 "ring_prog", "blur_prog", "comp_prog", "flash_prog")
        for n in names:
            obj = self.__dict__.pop(n, None)
            if obj is not None:
                try:
                    obj.release()
                except Exception:
                    pass
        try:
            self.ctx.release()
        except Exception:
            pass

    def _make_programs(self):
        mgl = self.mgl
        quad_vs = """
            #version 330
            in vec2 in_pos;
            in vec2 i_pos;
            in vec4 i_color;
            in vec2 i_misc;
            uniform vec2 u_view;
            out vec2 v_uv;
            out vec4 v_color;
            void main() {
                float cs = cos(i_misc.y);
                float sn = sin(i_misc.y);
                vec2 q = in_pos * i_misc.x;
                q = vec2(q.x * cs - q.y * sn, q.x * sn + q.y * cs);
                vec2 p = (i_pos + q) / u_view * 2.0 - 1.0;
                p.y = -p.y;
                gl_Position = vec4(p, 0.0, 1.0);
                v_uv = in_pos * 0.5 + 0.5;
                v_color = i_color;
            }
        """
        particle_fs = """
            #version 330
            in vec2 v_uv;
            in vec4 v_color;
            out vec4 frag;
            void main() {
                float d = distance(v_uv, vec2(0.5));
                float halo = smoothstep(0.50, 0.08, d);
                float core = smoothstep(0.30, 0.02, d);
                float a = (halo * 0.34 + core * 0.92) * v_color.a;
                vec3 rgb = mix(v_color.rgb, vec3(1.0), core * 0.68);
                frag = vec4(rgb, a);
            }
        """
        ring_vs = """
            #version 330
            in vec2 in_pos;
            in vec4 in_color;
            uniform vec2 u_view;
            out vec4 v_color;
            void main() {
                vec2 p = in_pos / u_view * 2.0 - 1.0;
                p.y = -p.y;
                gl_Position = vec4(p, 0.0, 1.0);
                v_color = in_color;
            }
        """
        ring_fs = """
            #version 330
            in vec4 v_color;
            out vec4 frag;
            void main() { frag = v_color; }
        """
        post_vs = """
            #version 330
            in vec2 in_pos;
            out vec2 v_uv;
            void main() {
                gl_Position = vec4(in_pos, 0.0, 1.0);
                v_uv = in_pos * 0.5 + 0.5;
            }
        """
        blur_fs = """
            #version 330
            uniform sampler2D u_tex;
            uniform vec2 u_dir;
            in vec2 v_uv;
            out vec4 frag;
            void main() {
                vec2 px = 1.0 / vec2(textureSize(u_tex, 0));
                vec4 sum = texture(u_tex, v_uv) * 0.227027;
                sum += texture(u_tex, v_uv + u_dir * px * 1.384615) * 0.316216;
                sum += texture(u_tex, v_uv - u_dir * px * 1.384615) * 0.316216;
                sum += texture(u_tex, v_uv + u_dir * px * 3.230769) * 0.070270;
                sum += texture(u_tex, v_uv - u_dir * px * 3.230769) * 0.070270;
                frag = sum;
            }
        """
        composite_fs = """
            #version 330
            uniform sampler2D u_blur;
            uniform sampler2D u_scene;
            in vec2 v_uv;
            out vec4 frag;
            void main() {
                vec4 b = texture(u_blur, v_uv);
                vec4 s = texture(u_scene, v_uv);
                vec3 rgb = b.rgb * 1.25 + s.rgb;
                float a = max(s.a, min(0.98, b.a * 0.82 + s.a));
                frag = vec4(rgb, a);
            }
        """
        flash_fs = """
            #version 330
            uniform vec4 u_flash;
            in vec2 v_uv;
            out vec4 frag;
            void main() {
                float d = distance(v_uv, vec2(0.5));
                float vignette = smoothstep(0.75, 0.1, d);
                frag = vec4(u_flash.rgb, u_flash.a * (0.55 + vignette * 0.45));
            }
        """
        self.particle_prog = self.ctx.program(vertex_shader=quad_vs, fragment_shader=particle_fs)
        self.ring_prog = self.ctx.program(vertex_shader=ring_vs, fragment_shader=ring_fs)
        self.blur_prog = self.ctx.program(vertex_shader=post_vs, fragment_shader=blur_fs)
        self.comp_prog = self.ctx.program(vertex_shader=post_vs, fragment_shader=composite_fs)
        self.flash_prog = self.ctx.program(vertex_shader=post_vs, fragment_shader=flash_fs)

    def _make_buffers(self):
        mgl = self.mgl
        quad = array("f", [-1,-1, 1,-1, 1,1, -1,-1, 1,1, -1,1])
        self.quad_vbo = self.ctx.buffer(quad.tobytes())
        # pos xy, color rgba, size+rotation. Per-instance divisor is /i.
        self.inst_vbo = self.ctx.buffer(reserve=4 * 8 * 900, dynamic=True)
        self.particle_vao = self.ctx.vertex_array(
            self.particle_prog,
            [
                (self.quad_vbo, "2f", "in_pos"),
                (self.inst_vbo, "2f/i 4f/i 2f/i", "i_pos", "i_color", "i_misc"),
            ],
        )
        self.ring_vbo = self.ctx.buffer(reserve=4 * 6 * 80 * 96, dynamic=True)
        self.ring_vao = self.ctx.vertex_array(
            self.ring_prog,
            [(self.ring_vbo, "2f 4f", "in_pos", "in_color")],
        )
        self.post_vao = self.ctx.simple_vertex_array(self.blur_prog, self.quad_vbo, "in_pos")
        self.post_comp_vao = self.ctx.simple_vertex_array(self.comp_prog, self.quad_vbo, "in_pos")
        self.flash_vao = self.ctx.simple_vertex_array(self.flash_prog, self.quad_vbo, "in_pos")

    def _make_targets(self, w, h):
        w, h = max(64, int(w)), max(64, int(h))
        self.size = (w, h)
        # Half-res bloom is intentionally cheaper and gives a softer glow.
        bw, bh = max(32, w // 2), max(32, h // 2)
        if hasattr(self, "scene_tex"):
            for obj in (self.scene_tex, self.blur_a, self.blur_b, self.scene_fbo, self.blur_fbo_a, self.blur_fbo_b):
                try: obj.release()
                except Exception: pass
        self.scene_tex = self.ctx.texture((bw, bh), 4, dtype="f1")
        self.blur_a = self.ctx.texture((bw, bh), 4, dtype="f1")
        self.blur_b = self.ctx.texture((bw, bh), 4, dtype="f1")
        for tex in (self.scene_tex, self.blur_a, self.blur_b):
            tex.filter = (self.mgl.LINEAR, self.mgl.LINEAR)
        self.scene_fbo = self.ctx.framebuffer(color_attachments=[self.scene_tex])
        self.blur_fbo_a = self.ctx.framebuffer(color_attachments=[self.blur_a])
        self.blur_fbo_b = self.ctx.framebuffer(color_attachments=[self.blur_b])

    @staticmethod
    def _hex_rgb(value: str):
        if not isinstance(value, str):
            return (1.0, 1.0, 1.0)
        s = value.strip().lstrip("#")
        if len(s) != 6:
            return (1.0, 1.0, 1.0)
        try:
            return tuple(int(s[i:i+2], 16) / 255.0 for i in (0,2,4))
        except ValueError:
            return (1.0, 1.0, 1.0)

    def _instances(self, snap):
        out = array("f")
        particles = snap.get("particles", ())
        # Re-sort by life so fresh particles sit visually over older glow.
        particles = particles[-760:]
        for p in particles:
            life = max(0.0, min(1.0, float(p.get("life", 0.0)) / max(0.001, float(p.get("max", 1.0)))))
            alpha = max(0.0, min(1.0, life * 1.7))
            rgb = self._hex_rgb(p.get("col", "#ffffff"))
            x = float(p.get("sx", p.get("x", 0.0)))
            y = float(p.get("sy", p.get("y", 0.0)))
            size = float(p.get("size_px", 4.0))
            ang = float(p.get("angle", 0.0))
            out.extend((x, y, rgb[0], rgb[1], rgb[2], alpha, size, ang))
        return out

    def draw(self, snap, geometry):
        x, y, w, h, visible = geometry
        if not visible or w < 2 or h < 2:
            self.ctx.screen.use()
            self.ctx.screen.clear(0.0, 0.0, 0.0, 0.0)
            return
        if (w, h) != self.size:
            self._make_targets(w, h)
        self.window.switch_to()
        mgl = self.mgl
        self._render_scene(snap, w, h)
        # Blur horizontal.
        self.blur_fbo_a.use()
        self.ctx.clear(0.0, 0.0, 0.0, 0.0)
        self.scene_tex.use(0)
        self.blur_prog["u_tex"].value = 0
        self.blur_prog["u_dir"].value = (1.0, 0.0)
        self.post_vao.render(mode=mgl.TRIANGLES)
        # Blur vertical.
        self.blur_fbo_b.use()
        self.ctx.clear(0.0, 0.0, 0.0, 0.0)
        self.blur_a.use(0)
        self.blur_prog["u_dir"].value = (0.0, 1.0)
        self.post_vao.render(mode=mgl.TRIANGLES)
        # Composite to the transparent overlay framebuffer.
        self.ctx.screen.use()
        self.ctx.clear(0.0, 0.0, 0.0, 0.0)
        self.ctx.blend_func = (mgl.SRC_ALPHA, mgl.ONE)
        self.blur_b.use(0)
        self.scene_tex.use(1)
        self.comp_prog["u_blur"].value = 0
        self.comp_prog["u_scene"].value = 1
        self.post_comp_vao.render(mode=mgl.TRIANGLES)
        # Crisp screen flash on top, but still alpha-composited.
        fp = float(snap.get("flash_power", 0.0))
        if fp > 0.002:
            rgb = self._hex_rgb(snap.get("flash_col", "#ffffff"))
            a = max(0.0, min(0.55, fp))
            self.ctx.blend_func = (mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA)
            self.flash_prog["u_flash"].value = (rgb[0], rgb[1], rgb[2], a)
            self.flash_vao.render(mode=mgl.TRIANGLES)
        self.ctx.screen.finish()

    def _render_scene(self, snap, w, h):
        mgl = self.mgl
        self.scene_fbo.use()
        self.ctx.clear(0.0, 0.0, 0.0, 0.0)
        inst = self._instances(snap)
        if inst:
            self.inst_vbo.write(inst.tobytes())
            self.particle_prog["u_view"].value = (float(w), float(h))
            self.ctx.blend_func = (mgl.SRC_ALPHA, mgl.ONE)
            self.particle_vao.render(mode=mgl.TRIANGLES, instances=len(inst) // 8)

        # Rings: procedural on the CPU, rasterised by OpenGL as a single line batch.
        verts = array("f")
        for r in snap.get("rings", ())[-80:]:
            life = max(0.0, min(1.0, float(r.get("life", 0.0)) / max(0.001, float(r.get("max", 1.0)))))
            age = 1.0 - life
            cx = float(r.get("sx", r.get("x", 0.0)))
            cy = float(r.get("sy", r.get("y", 0.0)))
            rr = max(1.0, float(r.get("radius_px", 8.0)) * (0.55 + age * 0.75))
            start = math.radians(float(r.get("start", 0.0)) + age * 35.0)
            extent = math.radians(float(r.get("extent", 270.0)))
            rr_y = rr * 0.82
            rgb = self._hex_rgb(r.get("col", "#ffffff"))
            a = max(0.0, min(1.0, life * 1.4))
            seg = max(10, int(abs(extent) * 0.22))
            for i in range(seg + 1):
                ang = start + extent * (i / seg)
                verts.extend((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr_y, rgb[0], rgb[1], rgb[2], a))
        if verts:
            self.ring_vbo.write(verts.tobytes())
            self.ring_prog["u_view"].value = (float(w), float(h))
            self.ctx.blend_func = (mgl.SRC_ALPHA, mgl.ONE)
            self.ring_vao.render(mode=mgl.LINE_STRIP)
