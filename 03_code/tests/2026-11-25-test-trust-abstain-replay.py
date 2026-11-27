#!/usr/bin/env python3
"""EXP-045 arm A4 (external-audit finding T024, revision 2: gap only): controls of the trust/abstain cal-B replay.

1. Positive control. `2026-11-25-trust-abstain.py --check-only selector` (pool `E_cal[:cut - gap]`, gap = h - 1,
   lower clip 0 as the test band) must pass both inline controls at every facility: the replay reproduces the
   gamma and the cal-B covered count (`gamma_calB_picp` x `n_cal_b`) of the ACQR row (t+15, level 0.90) of
   `2026-11-22-core-belgrade-v3-gcal-per-facility.csv`, and the cal-B and test lower ends are clipped alike.
2. Negative control for the gap rule. `--check-only old` (the 2026-09-03 replay, pool `E_cal[:cut]`) must fail
   the replay control.
3. Negative control for the clip. `--check-only clipnone` (the gap rule with clip_low=None on cal-B) must pass
   the replay control (the clip never changes coverage) and fail the clip control, at least one facility.
4. Negative control for the clip on the test side (revision 61, 59b review note 9). `--check-only testclipnone`
   (clip_low=None on the test band the rows are computed from) must pass the replay control and fail the clip
   control: the control reads `lo_t` itself, so a test band that drops its clip is detected.
Run from the project root. Writes nothing.
"""
import subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SP = ROOT / "03_code" / "src" / "conformal" / "2026-11-25-trust-abstain.py"
# mode -> (expected exit, expected replay control, expected clip control)
CASES = [("selector", 0, "PASS", "PASS"), ("old", 1, "FAIL", "PASS"), ("clipnone", 1, "PASS", "FAIL"),
         ("testclipnone", 1, "PASS", "FAIL")]
fails = 0
for mode, want_rc, want_rep, want_clip in CASES:
    r = subprocess.run([sys.executable, str(SP), "--check-only", mode, "--budget", "99999"], cwd=ROOT,
                       capture_output=True, text=True)
    lines = r.stdout.splitlines() + r.stderr.splitlines()
    rep = next((l for l in lines if "REPLAY CONTROL" in l), "")
    clip = next((l for l in lines if "CLIP CONTROL" in l), "")
    got_rep = "PASS" if ": PASS" in rep else "FAIL"
    got_clip = "PASS" if ": PASS" in clip else "FAIL"
    ok = (r.returncode == want_rc) and (got_rep == want_rep) and (got_clip == want_clip) and rep and clip
    fails += 0 if ok else 1
    print(f"[{'PASS' if ok else 'FAIL'}] --check-only {mode}: exit {r.returncode} (expected {want_rc}), "
          f"replay {got_rep} (expected {want_rep}), clip {got_clip} (expected {want_clip})")
    print(f"       {rep.strip()}")
    print(f"       {clip.strip()}")
    for l in lines:
        if "MISMATCH" in l:
            print("       ", l.strip())
print("ALL PASS" if not fails else f"{fails} FAILURE(S)")
sys.exit(1 if fails else 0)
