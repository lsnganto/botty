"""Smoke test for human_mouse.py – runs without executing mouse movement (dry_run=True)."""
import sys
sys.path.insert(0, 'src')

from utils.human_mouse import (
    move_human_like, moveTo, HumanTrajectory,
    _fitts_time, _minimum_jerk_position, _fbm_1d
)

# ─── 1. Basic trajectory generation ──────────────────────────────────────────
traj = move_human_like(
    start_pos=(100.0, 100.0),
    end_pos=(800.0, 600.0),
    speed_factor=1.0,
    overshoot_probability=0.5,
    tremor_amplitude=1.2,
    dry_run=True,
)
assert len(traj.points) > 5, "Too few trajectory points"
assert traj.delays.sum() > 0.01, "Zero total duration"
print(f"[OK] Trajectory: {len(traj.points)} points, {traj.delays.sum():.3f}s total")

# ─── 2. Fitts's Law ───────────────────────────────────────────────────────────
mt = _fitts_time(700.0, 10.0, 1.0)
assert 0.05 < mt < 3.0, f"Fitts time out of range: {mt}"
print(f"[OK] Fitts law: distance=700px, target=10px → MT={mt:.3f}s")

# ─── 3. Minimum-Jerk profile ─────────────────────────────────────────────────
mj0 = _minimum_jerk_position(0.0)
mj5 = _minimum_jerk_position(0.5)
mj1 = _minimum_jerk_position(1.0)
assert abs(mj0) < 1e-9, f"Min-jerk should start at 0, got {mj0}"
assert abs(mj5 - 0.5) < 1e-9, f"Min-jerk mid should be 0.5, got {mj5}"
assert abs(mj1 - 1.0) < 1e-9, f"Min-jerk should end at 1, got {mj1}"
print(f"[OK] Min-jerk profile: τ=0→{mj0:.4f}, τ=0.5→{mj5:.4f}, τ=1→{mj1:.4f}")

# ─── 4. fBm noise ────────────────────────────────────────────────────────────
n0 = _fbm_1d(0.0, octaves=5, persistence=0.55, seed=42)
n1 = _fbm_1d(1.0, octaves=5, persistence=0.55, seed=42)
assert -2 < n0 < 2, f"fBm out of range: {n0}"
assert n0 != n1, "Noise should differ at different t"
print(f"[OK] fBm noise: t=0→{n0:.4f}, t=1→{n1:.4f}")

# ─── 5. Uniqueness – two calls must produce different paths ───────────────────
traj2 = move_human_like(
    start_pos=(100.0, 100.0),
    end_pos=(800.0, 600.0),
    dry_run=True,
)
# At least some points should differ (different RNG seed each call)
import numpy as np
n_common = min(len(traj.points), len(traj2.points))
diffs = np.abs(traj.points[:n_common] - traj2.points[:n_common]).max()
assert diffs > 0, "Two independent calls produced identical paths!"
print(f"[OK] Uniqueness: max diff between two calls = {diffs:.3f}px")

# ─── 6. AHK export ───────────────────────────────────────────────────────────
ahk_script = traj.to_ahk_script("")
assert "MouseMove" in ahk_script, "AHK export missing MouseMove commands"
assert "Sleep" in ahk_script, "AHK export missing Sleep commands"
assert "F10::" in ahk_script, "AHK export missing hotkey"
print(f"[OK] AHK export: {len(ahk_script.splitlines())} lines generated")

# ─── 7. Short-distance edge case (dist < 30 px → no overshoot) ───────────────
short = move_human_like(
    start_pos=(300.0, 300.0),
    end_pos=(305.0, 302.0),
    overshoot_probability=1.0,  # force overshoot flag, but dist too short
    dry_run=True,
)
assert len(short.points) >= 4, "Short move should still have points"
print(f"[OK] Short-distance move: {len(short.points)} points")

print()
print("=" * 50)
print("  ALL SMOKE TESTS PASSED")
print("=" * 50)
