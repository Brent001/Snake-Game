#!/usr/bin/env python3
"""Build Repair Terminal for Windows (.exe), Debian/Ubuntu (.deb), or Flatpak.

Examples:
  python scripts/build.py --target exe       # run on Windows
  python scripts/build.py --target deb       # run on Debian/Ubuntu
  python scripts/build.py --target flatpak   # run on Linux with Flatpak tooling installed
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.1.0"
APP_ID = "org.repairterminal.RepairTerminal"
APP_NAME = "RepairTerminal"


def run(command: list[str], *, cwd: Path = ROOT) -> None:
    print("+", " ".join(str(part) for part in command), flush=True)
    subprocess.run([str(part) for part in command], cwd=cwd, check=True)


def require_command(name: str, purpose: str) -> str:
    found = shutil.which(name)
    if not found:
        raise RuntimeError(f"Missing '{name}'. Install it to {purpose}.")
    return found


def make_pyinstaller_binary(platform_folder: str) -> Path:
    if platform.system() not in ("Windows", "Linux"):
        raise RuntimeError("PyInstaller packaging is currently configured for Windows and Linux only.")

    try:
        import PyInstaller  # noqa: F401
    except ImportError as exc:
        raise RuntimeError(
            "PyInstaller is not installed in this Python environment. Run:\n"
            "  python -m pip install -r requirements-build.txt"
        ) from exc

    dist_dir = ROOT / "dist" / platform_folder
    work_dir = ROOT / "build" / f"pyinstaller-{platform_folder}"
    spec_dir = ROOT / "build" / "spec"
    for folder in (dist_dir, work_dir):
        if folder.exists():
            shutil.rmtree(folder)
        folder.mkdir(parents=True, exist_ok=True)
    spec_dir.mkdir(parents=True, exist_ok=True)

    assets_dir = ROOT / "game" / "assets"
    data_separator = os.pathsep
    command = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm", "--clean", "--onefile", "--windowed",
        "--name", APP_NAME,
        "--distpath", str(dist_dir),
        "--workpath", str(work_dir),
        "--specpath", str(spec_dir),
        "--collect-submodules", "game",
        "--add-data", f"{assets_dir}{data_separator}game/assets",
        str(ROOT / "main.py"),
    ]
    run(command)

    binary = dist_dir / (f"{APP_NAME}.exe" if platform.system() == "Windows" else APP_NAME)
    if not binary.is_file():
        raise RuntimeError(f"PyInstaller reported success, but output was not found: {binary}")
    return binary


def build_exe() -> None:
    if platform.system() != "Windows":
        raise RuntimeError("The Windows .exe must be built on Windows. Run: python scripts/build.py --target exe")
    binary = make_pyinstaller_binary("windows")
    print(f"\nWindows executable built: {binary}")
    print("It is a one-file build; distribute this executable as-is.")


def build_deb() -> None:
    if platform.system() != "Linux":
        raise RuntimeError("The .deb target must be built on Linux (Debian/Ubuntu recommended).")
    require_command("dpkg-deb", "build a Debian package (install dpkg-dev)")

    stage = ROOT / "build" / "deb-root"
    if stage.exists():
        shutil.rmtree(stage)

    opt_dir = stage / "opt" / "repair-terminal"
    opt_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "main.py", opt_dir / "main.py")
    shutil.copytree(
        ROOT / "game", opt_dir / "game",
        # Never ship the source checkout's local settings/preferences.
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "settings.json"),
    )

    launcher = stage / "usr" / "bin" / "repair-terminal"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(
        "#!/bin/sh\n"
        "export REPAIR_USER_CONFIG=1\n"
        "cd /opt/repair-terminal\n"
        "exec python3 /opt/repair-terminal/main.py \"$@\"\n",
        encoding="utf-8",
    )
    launcher.chmod(0o755)

    desktop_file = stage / "usr" / "share" / "applications" / f"{APP_ID}.desktop"
    desktop_file.parent.mkdir(parents=True, exist_ok=True)
    desktop_file.write_text(
        "[Desktop Entry]\n"
        "Name=Repair Terminal\n"
        "Comment=Snake action-RPG with pixel-art biomes and boss encounters\n"
        "Exec=repair-terminal\n"
        f"Icon={APP_ID}\n"
        "Terminal=false\n"
        "Type=Application\n"
        "Categories=Game;ArcadeGame;\n"
        "StartupNotify=true\n",
        encoding="utf-8",
    )

    icon = stage / "usr" / "share" / "icons" / "hicolor" / "scalable" / "apps" / f"{APP_ID}.svg"
    icon.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "packaging" / "icons" / f"{APP_ID}.svg", icon)

    doc_dir = stage / "usr" / "share" / "doc" / "repair-terminal"
    doc_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / "CREDITS.txt", doc_dir / "CREDITS.txt")
    shutil.copy2(ROOT / "README.md", doc_dir / "README.md")

    control_dir = stage / "DEBIAN"
    control_dir.mkdir(parents=True, exist_ok=True)
    # Shared workspaces can propagate setgid to new directories. Strip special
    # permission bits throughout the package tree to produce normal package dirs.
    for directory in (stage, *[path for path in stage.rglob("*") if path.is_dir()]):
        directory.chmod(0o755)
    (control_dir / "control").write_text(
        f"Package: repair-terminal\n"
        f"Version: {VERSION}\n"
        "Section: games\n"
        "Priority: optional\n"
        "Architecture: all\n"
        "Maintainer: Repair Terminal Project\n"
        "Depends: python3 (>= 3.10), python3-tk\n"
        "Description: Pixel-art snake action-RPG\n"
        " Repair Terminal is a desktop action-RPG with multiple biomes,\n"
        " boss encounters, elemental combat, and skill trees.\n",
        encoding="utf-8",
    )

    output_dir = ROOT / "dist" / "linux"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"repair-terminal_{VERSION}_all.deb"
    if output.exists():
        output.unlink()
    run(["dpkg-deb", "--build", "--root-owner-group", str(stage), str(output)])
    print(f"\nDebian package built: {output}")


def build_flatpak() -> None:
    if platform.system() != "Linux":
        raise RuntimeError("The Flatpak target must be built on Linux.")
    require_command("flatpak-builder", "build a Flatpak")
    require_command("flatpak", "bundle a Flatpak")

    binary = make_pyinstaller_binary("linux")
    source_dir = ROOT / "build" / "flatpak-source"
    if source_dir.exists():
        shutil.rmtree(source_dir)
    source_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binary, source_dir / APP_NAME)
    (source_dir / APP_NAME).chmod(0o755)

    manifest = ROOT / "packaging" / "flatpak" / f"{APP_ID}.yml"
    build_dir = ROOT / "build" / "flatpak-build"
    repo_dir = ROOT / "build" / "flatpak-repo"
    if build_dir.exists():
        shutil.rmtree(build_dir)
    output_dir = ROOT / "dist" / "linux"
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = output_dir / "repair-terminal.flatpak"
    if bundle.exists():
        bundle.unlink()

    run(["flatpak-builder", "--force-clean", "--repo", str(repo_dir), str(build_dir), str(manifest)])
    run(["flatpak", "build-bundle", str(repo_dir), str(bundle), APP_ID, "stable"])
    print(f"\nFlatpak bundle built: {bundle}")
    print("Install prerequisites if needed: Flathub + org.freedesktop.Platform//25.08")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("exe", "deb", "flatpak"), required=True)
    args = parser.parse_args()

    builders = {"exe": build_exe, "deb": build_deb, "flatpak": build_flatpak}
    try:
        builders[args.target]()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"BUILD FAILED: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
