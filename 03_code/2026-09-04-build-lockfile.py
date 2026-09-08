#!/usr/bin/env python3
"""
R-PHASE 6 / R01 — build the exact environment lock from the RUNNING interpreter, not from a wish list.

Emits two artifacts:
  05_results/tables/2026-09-04-environment-recorded.csv   one row per package + one row per env fact
  03_code/2026-09-04-requirements.lock.txt                exact `==` pins with sha256 per wheel

WHY IT READS THE LIVE INTERPRETER
---------------------------------
`03_code/requirements.txt` floats every bound, omits `ngboost`, and lists `statsmodels`, which no script
in the live tree imports. Worse, the shipped README pins `mapie==1.4.1` while every published EnbPI number
was computed under **1.5.0** (EXP-025), and A13 measured that this exact difference already moved a
published number. A lock file retyped from those files would inherit all of it. This script therefore
records what the numbers were actually produced under, and `verify-state.sh deps` remains the check that
the two agree.

Digests: taken from the sha256-verified wheel cache left by `2026-09-03-restore-env.sh` where the package
was installed off-volume (A10/A14), and from the PyPI JSON API otherwise (the base-image packages).
Each row says which, so no digest is presented as more authoritative than it is.

Usage:  python 2026-09-04-build-lockfile.py [--no-network]
Overwrites nothing: both outputs are new dated files, and the script refuses if either already exists.
"""
from __future__ import annotations
import argparse, hashlib, json, os, platform, sys, urllib.request
from pathlib import Path

p = Path(__file__).resolve()
while p != p.parent and not (p / "01_data").is_dir():
    p = p.parent
ROOT = p
OUT_CSV = ROOT / "05_results" / "tables" / "2026-09-04-environment-recorded.csv"
OUT_LOCK = ROOT / "03_code" / "2026-09-04-requirements.lock.txt"

# pip name -> import name. Order is the order they appear in the lock file.
PKGS = [
    ("numpy", "numpy", "base-image"),
    ("pandas", "pandas", "base-image"),
    ("matplotlib", "matplotlib", "base-image"),
    ("pyarrow", "pyarrow", "off-volume"),
    ("scipy", "scipy", "off-volume"),
    ("scikit-learn", "sklearn", "off-volume"),
    ("joblib", "joblib", "off-volume"),
    ("threadpoolctl", "threadpoolctl", "off-volume"),
    ("cloudpickle", "cloudpickle", "off-volume"),
    ("mapie", "mapie", "off-volume"),
    ("ngboost", "ngboost", "off-volume"),
    ("tqdm", "tqdm", "off-volume"),
    ("holidays", "holidays", "off-volume"),
]
WHEEL_CACHE = Path(f"/tmp/pipwork-{os.getuid()}")


def log(m):
    print(f"[lock] {m}", flush=True)


def wheel_ok_for_platform(name: str) -> bool:
    if not name.endswith(".whl"):
        return False
    if "py3-none-any" in name:
        return True
    return "cp310" in name and "x86_64" in name and "musllinux" not in name and "macosx" not in name


def pypi_digest(pkg: str, ver: str):
    url = f"https://pypi.org/pypi/{pkg}/{ver}/json"
    d = json.load(urllib.request.urlopen(url, timeout=30))
    cands = [f for f in d["urls"] if wheel_ok_for_platform(f["filename"])]
    if not cands:
        cands = [f for f in d["urls"] if f["filename"].endswith(".tar.gz")]
    if not cands:
        return None, None
    cands.sort(key=lambda f: ("py3-none-any" not in f["filename"], f["filename"]))
    return cands[0]["filename"], cands[0]["digests"]["sha256"]


def local_digest(pkg: str, ver: str):
    stem = pkg.replace("-", "_")
    for f in sorted(WHEEL_CACHE.glob("*.whl")) if WHEEL_CACHE.is_dir() else []:
        n = f.name
        if (n.startswith(stem + "-") or n.startswith(pkg + "-")) and f"-{ver}-" in n:
            return n, hashlib.sha256(f.read_bytes()).hexdigest()
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-network", action="store_true")
    args = ap.parse_args()

    for f in (OUT_CSV, OUT_LOCK):
        if f.exists():
            sys.exit(f"[lock] REFUSING to overwrite existing {f.name} — supersede by date instead.")

    rows = []
    lock_lines = []
    for pkg, mod, origin in PKGS:
        try:
            m = __import__(mod)
            ver = getattr(m, "__version__", "?")
            loc = getattr(m, "__file__", "") or ""
        except Exception as e:
            rows.append(dict(kind="package", name=pkg, import_name=mod, version="IMPORT-FAILED",
                             origin=origin, wheel="", sha256="", digest_source=str(type(e).__name__),
                             installed_path=""))
            log(f"  {pkg}: IMPORT FAILED ({type(e).__name__})")
            continue
        whl, dig, src = None, None, ""
        whl, dig = local_digest(pkg, ver)
        if dig:
            src = "wheel-cache (sha256-verified at install, restore-env.sh)"
        elif not args.no_network:
            try:
                whl, dig = pypi_digest(pkg, ver)
                src = "pypi-json"
            except Exception as e:
                src = f"unavailable ({type(e).__name__})"
        rows.append(dict(kind="package", name=pkg, import_name=mod, version=ver, origin=origin,
                         wheel=whl or "", sha256=dig or "", digest_source=src,
                         installed_path=loc))
        lock_lines.append((pkg, ver, whl or "", dig or "", src))
        log(f"  {pkg}=={ver}  [{origin}]  {src}")

    # --- environment facts -------------------------------------------------------------------
    env = {
        "python_version": sys.version.split()[0],
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "libc": "-".join(x for x in platform.libc_ver() if x),
        "machine": platform.machine(),
        "cpu_count": str(os.cpu_count()),
    }
    try:
        import numpy
        c = numpy.show_config("dicts")
        bd = c.get("Build Dependencies", {})
        env["numpy_blas"] = f'{bd.get("blas",{}).get("name")} {bd.get("blas",{}).get("version")}'
        env["numpy_lapack"] = f'{bd.get("lapack",{}).get("name")} {bd.get("lapack",{}).get("version")}'
        env["numpy_c_compiler"] = str(c.get("Compilers", {}).get("c", {}).get("version"))
    except Exception as e:
        env["numpy_blas"] = f"unavailable ({type(e).__name__})"
    try:
        import threadpoolctl
        ti = threadpoolctl.threadpool_info()
        env["threadpool_info"] = json.dumps(ti) if ti else "[] (no BLAS/OpenMP layer reported)"
    except Exception as e:
        env["threadpool_info"] = f"unavailable ({type(e).__name__})"
    for k, v in env.items():
        rows.append(dict(kind="environment", name=k, import_name="", version=v, origin="", wheel="",
                         sha256="", digest_source="measured", installed_path=""))

    import csv
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    log(f"wrote {OUT_CSV.name} ({len(rows)} rows)")

    # --- lock file ---------------------------------------------------------------------------
    L = []
    L.append("# EXACT ENVIRONMENT LOCK — parking conformal-prediction project (R-Phase 6, R01)")
    L.append("# Generated by 03_code/2026-09-04-build-lockfile.py from the RUNNING interpreter that")
    L.append("# produced the reported numbers. Do not edit by hand; supersede by date.")
    L.append("#")
    L.append("# These are the versions every published number in the manuscript was computed under.")
    L.append("# They are NOT advisory. LESSONS_LOG A13 records a MEASURED case in this project where an")
    L.append("# unpinned MAPIE moved a published coverage number, and the previously shipped README")
    L.append("# instructed `mapie==1.4.1`, which is NOT the version used (1.5.0).")
    L.append("#")
    L.append("# `statsmodels` is deliberately ABSENT: no script in 03_code/src imports it.")
    L.append("# `holidays` is required only to rebuild features from raw; the analysis path does not use it.")
    L.append("#")
    for k, v in env.items():
        L.append(f"# {k}: {v}")
    L.append("#")
    L.append("# pip install --no-deps -r 2026-09-04-requirements.lock.txt")
    L.append("")
    for pkg, ver, whl, dig, src in lock_lines:
        if dig:
            L.append(f"{pkg}=={ver} \\")
            L.append(f"    --hash=sha256:{dig}  # {whl}  [{src}]")
        else:
            L.append(f"{pkg}=={ver}  # digest unavailable ({src})")
    OUT_LOCK.write_text("\n".join(L) + "\n")
    log(f"wrote {OUT_LOCK.name} ({len(lock_lines)} pins)")
    log("ALL DONE")


if __name__ == "__main__":
    main()
