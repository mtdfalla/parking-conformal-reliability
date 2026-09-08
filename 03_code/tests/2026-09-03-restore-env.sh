#!/usr/bin/env bash
# Environment restore. See LESSONS_LOG A10/A11/A12/A14.
#
# WHY THIS EXISTS: packages are installed OFF-VOLUME because /sessions has been running at 93-100%.
# TWO distinct failure modes have now been seen, and this script handles both:
#
#   A11 (revision 37) — /tmp/pylibs is WIPED between sessions while the .pth pointing at it SURVIVES,
#        so a fresh session inherits a pointer to an empty directory.
#   A14 (revision 38) — /tmp/pylibs SURVIVES but is owned by the PREVIOUS session's uid (shown as
#        nobody:nogroup) and is therefore NOT WRITABLE. pip --target then prints only
#        "WARNING: Target directory ... already exists" and installs NOTHING, so the script appears
#        to run correctly and fails at the final import. This script now probes writability and
#        falls back to a uid-scoped directory, keeping the inherited one on sys.path (it is
#        world-readable, so packages already there are still usable).
#   A14b (revision 38) — the BASE image is not guaranteed to carry the scientific stack either.
#        scipy, scikit-learn and joblib were all absent. They are pinned and installed here.
#
# Every wheel is sha256-verified against the PyPI JSON API before installation.
# Versions are PINNED to the EXP-025 lock (LESSONS_LOG A13: an unpinned dependency has ALREADY
# moved a published number in this project). Do not relax a pin to make an install succeed.
#
# The pyarrow wheel is 50 MB and has downloaded at ~280 kB/s, which can exceed one device_bash call.
# That is safe: wheels are cached in /tmp/pipwork-$UID and curl resumes with -C -, so just run the
# script again until it prints PASS. It is idempotent and exits 0 immediately if everything imports.
set -uo pipefail

# --- PINNED versions: the EXP-025 lock, plus the base stack added in revision 38 -------------------
PINS=("pyarrow 25.0.1" "mapie 1.5.0" "ngboost 0.5.11" "tqdm 4.70.0"
      "scipy 1.15.3" "scikit-learn 1.7.2" "joblib 1.6.0" "threadpoolctl 3.6.0"
      "cloudpickle 3.1.2" "holidays 0.103")
# import name for each pin, same order (pip name != import name for scikit-learn)
MODS=(pyarrow mapie ngboost tqdm scipy sklearn joblib threadpoolctl cloudpickle holidays)

INHERITED=/tmp/pylibs
OWN=/tmp/pylibs-$(id -u)
WORK=/tmp/pipwork-$(id -u)
CACHE=/tmp/pipcache-$(id -u)
SP="$HOME/.local/lib/python3.10/site-packages"
mkdir -p "$OWN" "$WORK" "$CACHE" "$SP" 2>/dev/null
export TMPDIR="$WORK" PIP_CACHE_DIR="$CACHE" PYTHONDONTWRITEBYTECODE=1

echo "[restore] disk:"; df -h / /revisions 2>/dev/null | tail -3

# --- A14: pick a WRITABLE target, and say which one and why --------------------------------------
if [ -d "$INHERITED" ] && [ -w "$INHERITED" ]; then
  TARGET="$INHERITED"
  echo "[restore] target=$INHERITED (writable)"
else
  TARGET="$OWN"
  if [ -d "$INHERITED" ]; then
    echo "[restore] NOTE: $INHERITED exists but is NOT writable by uid $(id -u) — it belongs to an"
    echo "[restore]       earlier stage (A14). Keeping it on sys.path for reading; installing to $OWN."
  else
    echo "[restore] target=$OWN ($INHERITED absent — the A11 case)"
  fi
fi

# --- wire BOTH directories in before importing, so an inherited package is found ------------------
{ [ -d "$INHERITED" ] && echo "$INHERITED"; echo "$TARGET"; } > "$SP/zz-offvolume-pylibs.pth"

need=""
for m in "${MODS[@]}"; do
  python3 -c "import $m" 2>/dev/null || need="$need $m"
done
if [ -z "$need" ]; then echo "[restore] PASS — all ${#MODS[@]} pinned packages importable"; exit 0; fi
echo "[restore] missing:$need"

get () {  # get <pip-name> <version>
  python3 - "$1" "$2" "$WORK" <<'PY'
import json, sys, urllib.request, hashlib, os, subprocess
pkg, ver, work = sys.argv[1], sys.argv[2], sys.argv[3]
d = json.load(urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/{ver}/json"))
# Pick the wheel for THIS platform. Matching "cp310" alone is not enough: pyarrow also ships a
# cp310 macOS arm64 wheel, and an earlier version of this script downloaded it and then failed with
# "not a supported wheel on this platform" (lesson C8). Pure-python wheels are preferred.
def ok(n):
    if not n.endswith(".whl"):
        return False
    if "py3-none-any" in n:
        return True
    return "cp310" in n and "x86_64" in n and "manylinux" in n and "musllinux" not in n
cands = [f for f in d["urls"] if ok(f["filename"])]
if not cands:
    print("NO SUITABLE WHEEL", pkg); sys.exit(1)
cands.sort(key=lambda f: 0 if "py3-none-any" in f["filename"] else 1)
f = cands[0]
path = os.path.join(work, f["filename"])
if not (os.path.exists(path) and hashlib.sha256(open(path,'rb').read()).hexdigest() == f["digests"]["sha256"]):
    subprocess.run(["curl","-sS","-L","-C","-","-o",path,f["url"]], check=True)
got = hashlib.sha256(open(path,'rb').read()).hexdigest()
if got != f["digests"]["sha256"]:
    print("SHA256 MISMATCH", pkg); sys.exit(1)
print("OK", path)
PY
}

for i in "${!PINS[@]}"; do
  set -- ${PINS[$i]}
  mod="${MODS[$i]}"
  python3 -c "import $mod" 2>/dev/null && continue
  echo "[restore] fetching $1 $2 (sha256-verified, pinned)"
  OUT=$(get "$1" "$2") || { echo "  FAIL fetching $1 — if this was a download timeout, just run this"
                            echo "  script again: wheels are cached in $WORK and curl resumes with -C -."
                            exit 1; }
  WHL=$(echo "$OUT" | awk '/^OK/{print $2}')
  pip install --no-cache-dir --no-deps --target "$TARGET" "$WHL" 2>&1 | tail -1
done

python3 - <<'PY' || { echo "[restore] FAIL — imports still broken"; exit 1; }
import sys
lock = {"pyarrow":"25.0.1","mapie":"1.5.0","scipy":"1.15.3","sklearn":"1.7.2",
        "numpy":"2.2.6","pandas":"2.3.3"}
bad = []
for m in ["pyarrow","mapie","ngboost","tqdm","scipy","sklearn","joblib",
          "threadpoolctl","cloudpickle","holidays","numpy","pandas"]:
    try:
        v = getattr(__import__(m), "__version__", "?")
    except Exception as e:
        bad.append(f"{m}: {type(e).__name__}"); continue
    if m in lock and v != lock[m]:
        bad.append(f"{m}: {v} != pinned {lock[m]}")
if bad:
    print("[restore] LOCK/IMPORT FAILURES:"); [print("   ", b) for b in bad]; sys.exit(1)
print("[restore] PASS — 12 packages importable, all pinned versions match the EXP-025 lock")
PY
