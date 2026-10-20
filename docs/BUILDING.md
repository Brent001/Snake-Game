# Building Repair Terminal

Repair Terminal is a Python 3.10+ desktop game using the standard-library `tkinter` GUI. The main game does not require pip-installed runtime libraries. On Debian/Ubuntu, `tkinter` is supplied by the OS package `python3-tk`; it cannot be installed by pip. The optional Windows-first GPU VFX dependencies are in `requirements-gpu.txt`.

## Run from source

```sh
python -m pip install -r requirements.txt
python main.py
```

If a Linux Python installation is missing Tkinter, install it from the OS package manager first:

```sh
sudo apt install python3-tk
```

## Windows `.exe`

Use PowerShell from the repository root:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\build.ps1
```

Or manually:

```powershell
py -3 -m venv .venv-build
.\.venv-build\Scripts\python.exe -m pip install -r requirements-build.txt
.\.venv-build\Scripts\python.exe scripts/build.py --target exe
```

The output is `dist/windows/RepairTerminal.exe`. Build Windows executables on Windows; PyInstaller does not cross-compile a Windows binary from Linux. The generated app is a one-file executable with game art and audio bundled inside.

## Debian/Ubuntu `.deb`

Install the OS packaging and Tkinter dependencies, then run the build script:

```sh
sudo apt install python3 python3-tk dpkg-dev
./scripts/build.sh deb
```

The output is `dist/linux/repair-terminal_0.1.0_all.deb`. Installation example:

```sh
sudo apt install ./dist/linux/repair-terminal_0.1.0_all.deb
```

The package installs the application under `/opt/repair-terminal`, adds an application-menu entry, and stores mutable settings in the user's config directory rather than the root-owned application directory.

## Flatpak

Flatpak builds require Linux, `flatpak`, `flatpak-builder`, PyInstaller, and the Freedesktop 25.08 runtime and SDK. Install the runtime/SDK from Flathub if not already installed:

```sh
sudo apt install flatpak flatpak-builder python3-venv python3-tk
flatpak remote-add --if-not-exists --user flathub https://flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.freedesktop.Platform//25.08 org.freedesktop.Sdk//25.08
./scripts/build.sh flatpak
```

The output is `dist/linux/repair-terminal.flatpak`. Install it with:

```sh
flatpak install --user ./dist/linux/repair-terminal.flatpak
```

The Flatpak wraps a Linux PyInstaller build and requests access to the display, audio socket, GPU device, and its own app-specific settings directory. The Flatpak should still be tested on the target desktop/runtime before redistribution.

## CI

`.github/workflows/ci.yml` runs compilation and headless data checks, then builds a `.deb`, Windows `.exe`, and Flatpak artifact on their appropriate hosted runners. Download the outputs from the workflow run's **Artifacts** section.

## Dependency files

- `requirements.txt`: documents the runtime setup; core imports use the Python standard library and OS-provided Tkinter.
- `requirements-build.txt`: PyInstaller used by standalone executable/Flatpak builds.
- `requirements-dev.txt`: test tooling.
- `requirements-gpu.txt`: optional pyglet/ModernGL effects backend (currently Windows-first).
- `requirements-tools.txt`: optional Pillow/NumPy used to regenerate source art/audio assets.

## Project layout

- `game/`: runtime game package and bundled art/audio.
- `docs/changelog/`: historical release/change notes.
- `docs/development/`: design and renderer notes.
- `tools/assets/`: art/audio generation scripts.
- `tools/bench/`: benchmark utilities.
- `tools/manual_tests/`: interactive/manual debugging scripts; some depend on a graphical desktop or old local paths and are intentionally not part of headless CI.
- `tests/`: fast headless checks suitable for CI.
