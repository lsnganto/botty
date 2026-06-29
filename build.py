import os
import shutil
from pathlib import Path
from src.version import __version__
import argparse
import getpass
import random
from cryptography.fernet import Fernet
import string


parser = argparse.ArgumentParser(description="Build Sword")
parser.add_argument(
    "-v" , "--version",
    type=str,
    help="New release version e.g. 0.4.2",
    default=""
)
parser.add_argument(
    "-c", "--conda_path",
    type=str,
    help="Path to local conda e.g. C:\\Users\\USER\\miniconda3",
    default=f"C:\\Users\\{getpass.getuser()}\\miniconda3")
parser.add_argument(
    "-r", "--random_name",
    action='store_true',
    help="Will generate a random name for the sword exe")
parser.add_argument(
    "-k", "--use_key",
    action='store_true',
    help="Will build with encryption key")
parser.add_argument(
    "--no-gui",
    action='store_true',
    help="Skip building the GUI launcher (launcher_gui.exe)")
args = parser.parse_args()


# ─── Helpers ────────────────────────────────────────────────────────────────

def clean_up():
    """Remove PyInstaller build artefacts."""
    for name in ["build", "main.spec", "health_manager.spec",
                 "shopper.spec", "launcher_gui.spec"]:
        if os.path.isdir(name):
            shutil.rmtree(name)
        elif os.path.isfile(name):
            os.remove(name)


def pyinstaller_cmd(script: str, dist_dir: str, conda_path: str,
                    key_cmd: str = " ", extra_args: str = "") -> str:
    """Return a pyinstaller command string for a given script."""
    return (
        f"python -m PyInstaller --onefile --distpath {dist_dir}{key_cmd}"
        f" --exclude-module graphviz"
        f" --paths .\\src"
        f" --paths {conda_path}\\envs\\sword\\Lib\\site-packages"
        f"{extra_args}"
        f" src\\{script}"
    )


def build_gui_launcher(dist_dir: str, conda_path: str):
    """
    Build launcher_gui.exe — the PyQt6 configuration GUI.

    Uses a dedicated entry point (src/launcher/app.py) so the executable
    is self-contained and does NOT require the keyboard / bot modules at
    startup.  PyInstaller hidden-import flags ensure PyQt6 plugins are
    bundled correctly.
    """
    print("\n[GUI] Building launcher_gui.exe ...")

    # PyQt6 requires the Qt platform plugin DLLs to be included
    pyqt6_hooks = (
        " --hidden-import PyQt6"
        " --hidden-import PyQt6.QtWidgets"
        " --hidden-import PyQt6.QtCore"
        " --hidden-import PyQt6.QtGui"
        " --hidden-import PyQt6.sip"
        # collect all data files shipped with PyQt6 (platform plugins etc.)
        " --collect-all PyQt6"
    )

    # Bundle the QSS stylesheet as a data file so it is accessible at runtime
    # Format:  src/launcher/style.qss;launcher   (source;dest_folder_inside_exe)
    qss_data = " --add-data \"src\\\\launcher\\\\style.qss;launcher\""

    cmd = (
        f"python -m PyInstaller --onefile --distpath {dist_dir}"
        f" --name launcher_gui"
        f" --windowed"          # no console window for the GUI exe
        f" --exclude-module graphviz"
        f" --paths .\\src"
        f" --paths {conda_path}\\envs\\sword\\Lib\\site-packages"
        f"{pyqt6_hooks}"
        f"{qss_data}"
        f" src\\launcher\\app.py"
    )
    os.system(cmd)
    print("[GUI] launcher_gui.exe build complete.")


# ─── Main ────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    new_version_code = None
    if args.version != "":
        print(f"Releasing new version: {args.version}")
        os.system(f"git checkout -b new-release-v{args.version}")
        sword_dir = f"dist/sword_v{args.version}"
        version_code = ""
        with open('src/version.py', 'r') as f:
            version_code = f.read()
        version_code = version_code.split("=")
        new_version_code = f"{version_code[0]}= '{args.version}'"
        with open('src/version.py', 'w') as f:
            f.write(new_version_code)
    else:
        sword_dir = f"dist/sword_v{__version__}"
        print(f"Building version: {__version__}")

    os.makedirs("dist", exist_ok=True)

    clean_up()

    if os.path.exists(sword_dir):
        for path in Path(sword_dir).glob("**/*"):
            if path.is_file():
                os.remove(path)
            elif path.is_dir():
                shutil.rmtree(path)
        shutil.rmtree(sword_dir)

    # ── Build bot executables (main.py + shopper.py) ──────────────────
    for exe in ["main.py", "shopper.py"]:
        key_cmd = " "
        if args.use_key:
            key = Fernet.generate_key().decode("utf-8")
            key_cmd = " --key " + key
        os.system(pyinstaller_cmd(exe, sword_dir, args.conda_path, key_cmd))

    # ── Build GUI launcher ────────────────────────────────────────────
    if not args.no_gui:
        build_gui_launcher(sword_dir, args.conda_path)
    else:
        print("[GUI] Skipped (--no-gui flag set).")

    # ── Copy config & assets into dist folder ────────────────────────
    os.system(f"cd {sword_dir} && mkdir config && cd ..")

    with open(f"{sword_dir}/config/custom.ini", "w") as f:
        f.write("; Add parameters you want to overwrite from param.ini here")
    shutil.copy("config/game.ini",    f"{sword_dir}/config/")
    shutil.copy("config/params.ini",  f"{sword_dir}/config/")
    shutil.copy("config/shop.ini",    f"{sword_dir}/config/")
    shutil.copy("config/default.bnip",f"{sword_dir}/config/")
    os.makedirs(f"{sword_dir}/config/bnip", exist_ok=True)
    shutil.copy("README.md",          f"{sword_dir}/")
    shutil.copy("run_gui.bat",        f"{sword_dir}/")   # include GUI shortcut
    shutil.copytree("assets",         f"{sword_dir}/assets")

    clean_up()

    # ── Optional: randomise main.exe name ────────────────────────────
    if args.random_name:
        print("Generate random names")
        new_name = ''.join(random.choices(string.ascii_letters, k=random.randint(6, 14)))
        os.rename(f'{sword_dir}/main.exe', f'{sword_dir}/{new_name}.exe')

    # ── Git commit for version bump ───────────────────────────────────
    if new_version_code is not None:
        os.system(f'git add .')
        os.system(f'git commit -m "Bump version to v{args.version}"')

    print(f"\n✅  Build finished → {sword_dir}/")
    print(f"   main.exe         — CLI bot (original)")
    print(f"   shopper.exe      — Shopper bot")
    if not args.no_gui:
        print(f"   launcher_gui.exe — GUI configuration launcher")
    print(f"   run_gui.bat      — Double-click shortcut for GUI")
