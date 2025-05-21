#!/usr/bin/env python3

import os
import sys
import subprocess
import json
import shutil
import platform
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# 🎨 Terminal colors
class Color:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format=f"{Color.CYAN}%(asctime)s{Color.RESET} [{os.path.splitext(os.path.basename(__file__))[0]}:%(levelname)s] %(message)s",
        datefmt="%H:%M:%S"
    )

def log_info(msg, emoji="ℹ️"):
    logging.info(f"{emoji} {msg}")

def log_success(msg, emoji="✅"):
    logging.info(f"{Color.GREEN}{emoji} {msg}{Color.RESET}")

def log_error(msg, emoji="❌"):
    logging.error(f"{Color.RED}{emoji} {msg}{Color.RESET}")

def log_warning(msg, emoji="⚠️"):
    logging.warning(f"{Color.YELLOW}{emoji} {msg}{Color.RESET}")

# ⚙️ Shell wrappers
def run_live(cmd, check=False, **kwargs):
    return subprocess.run(cmd, shell=True, check=check, stdout=sys.stdout, stderr=sys.stderr, **kwargs)

def run_capture(cmd, check=False, **kwargs):
    return subprocess.run(cmd, shell=True, check=check, capture_output=True, text=True, **kwargs)

# 🧰 Utilities
def brew_path():
    arch = platform.machine()
    if arch == "arm64":
        brew = "/opt/homebrew/bin/brew"
    elif arch == "x86_64":
        brew = "/usr/local/bin/brew"
    else:
        brew = shutil.which("brew")

    if brew and Path(brew).exists():
        return brew

    fallback = shutil.which("brew")
    if fallback:
        return fallback

    log_error("Homebrew not found in expected locations.")
    sys.exit(1)

def install_homebrew():
    log_info("Installing Homebrew... 🛠️")
    script_url = "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
    subprocess.run(f'/bin/bash -c "$(curl -fsSL {script_url})"', shell=True, check=True)
    return brew_path()

def parse_config(config_path="config.json"):
    if not Path(config_path).exists():
        log_error(f"Missing config file: {config_path}")
        sys.exit(1)
    with open(config_path) as f:
        return json.load(f)

def assert_lists(data, key):
    assert isinstance(data.get(key, []), list), f"{key} must be a list in config.json"

def get_caveat(brew, name, is_cask=False):
    flag = "--cask" if is_cask else ""
    result = run_capture(f"{brew} info {flag} --caveats {name}")
    caveat = result.stdout.strip()
    return {"cask" if is_cask else "formula": name, "caveat": caveat} if caveat else None

def collect_caveats_parallel(brew, formulae, casks):
    log_info("🔍 Collecting caveats in parallel...")

    items = [(name, False) for name in formulae] + [(name, True) for name in casks]
    caveats = []

    with ThreadPoolExecutor(max_workers=min(8, len(items))) as executor:
        futures = {executor.submit(get_caveat, brew, name, is_cask): (name, is_cask) for name, is_cask in items}
        for future in as_completed(futures):
            result = future.result()
            if result:
                caveats.append(result)

    return caveats

# 🔄 Brew operations
def update_and_upgrade(brew, result):
    log_info("Updating Homebrew... 🔄")
    run_live(f"{brew} update")

    log_info("Checking for outdated formulae... 📈")
    outdated = run_capture(f"{brew} outdated --formula --quiet").stdout.splitlines()
    if outdated:
        log_info(f"Upgrading: {' '.join(outdated)} ⏫")
        try:
            run_live(f"{brew} upgrade {' '.join(outdated)}", check=True)
            result["success"]["upgrade"]["formula"].extend(outdated)
        except Exception:
            result["error"]["upgrade"]["formula"].extend(outdated)
            log_error("One or more upgrades failed.")
    else:
        log_info("No formulae to upgrade. 👍")

def install_formulae(brew, formulae, result):
    installed = set(run_capture(f"{brew} list --formula").stdout.splitlines())
    to_install = [name for name in formulae if name not in installed]

    if to_install:
        log_info(f"Installing formulae: {' '.join(to_install)} 📦")
        try:
            run_live(f"{brew} install {' '.join(to_install)}", check=True)
            result["success"]["install"]["formula"].extend(to_install)
        except Exception:
            result["error"]["install"]["formula"].extend(to_install)
            log_error("Failed to install one or more formulae.")

def is_cask_installed(brew, name):
    methods = [
        lambda: name in run_capture(f"{brew} list --cask").stdout.splitlines(),
        lambda: "Not installed" not in run_capture(f"{brew} info --cask {name}").stdout,
        lambda: any(Path(p).exists() for p in [f"/Applications/{name}.app", f"{Path.home()}/Applications/{name}.app"])
    ]
    return any(m() for m in methods)

def filter_missing_casks_parallel(brew, casks):
    log_info("🧪 Checking for installed casks in parallel...")
    to_install = []

    with ThreadPoolExecutor(max_workers=min(8, len(casks))) as executor:
        futures = {executor.submit(is_cask_installed, brew, name): name for name in casks}
        for future in as_completed(futures):
            name = futures[future]
            try:
                if not future.result():
                    to_install.append(name)
            except Exception:
                log_warning(f"Failed to check cask: {name}")
                to_install.append(name)  # assume missing on error

    return to_install

def install_casks(brew, casks, result):
    to_install = filter_missing_casks_parallel(brew, casks)

    if to_install:
        log_info(f"Installing casks: {' '.join(to_install)} 🍺")
        try:
            run_live(f"{brew} install --cask {' '.join(to_install)}", check=True)
            result["success"]["install"]["cask"].extend(to_install)
        except Exception:
            result["error"]["install"]["cask"].extend(to_install)
            log_error("Failed to install one or more casks.")

# 📜 Final output
def print_result(result):
    result["success"]["cask"] = result["success"]["install"]["cask"]
    result["error"]["cask"] = result["error"]["install"]["cask"]

    print()
    log_info("📊 Final result:")
    print(Color.BOLD + json.dumps(result, indent=2, ensure_ascii=False) + Color.RESET)

# 🛑 Require macOS
def require_macos():
    if platform.system() != "Darwin":
        log_error("Error: This script can only be run on macOS. 🍏")
        sys.exit(1)

# 🧠 Orchestration
def main():
    setup_logging()
    require_macos()
    log_info("✨ Brew Sync Starting... 🚀")

    config = parse_config("config.json")
    assert_lists(config, "formula")
    assert_lists(config, "cask")
    formulae = config.get("formula", [])
    casks = config.get("cask", [])

    result = {
        "success": {"install": {"formula": [], "cask": []}, "upgrade": {"formula": []}, "cask": []},
        "error": {"install": {"formula": [], "cask": []}, "upgrade": {"formula": []}, "cask": []},
        "info": []
    }

    brew = brew_path()
    if not brew:
        brew = install_homebrew()
    os.environ["PATH"] = f"{str(Path(brew).parent)}:{os.environ['PATH']}"

    update_and_upgrade(brew, result)
    install_formulae(brew, formulae, result)
    install_casks(brew, casks, result)

    result["info"] = collect_caveats_parallel(brew, formulae, casks)
    print_result(result)

    log_success("🎉 Done!")

if __name__ == "__main__":
    main()
