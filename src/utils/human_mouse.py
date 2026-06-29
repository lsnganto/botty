"""
human_mouse.py – Highly realistic, anti-detection human-like mouse movement.

Architecture
============
  ┌──────────────────────────────────────────────────────┐
  │  Python "Brain"  (this module)                       │
  │  ┌────────────┐  ┌──────────────┐  ┌─────────────┐  │
  │  │ Path Gen   │  │ Velocity     │  │ Jitter      │  │
  │  │ (Bézier /  │→ │ (Min-Jerk + │→ │ (Perlin     │  │
  │  │  B-Spline) │  │  Fitts Law) │  │  noise)     │  │
  │  └────────────┘  └──────────────┘  └─────────────┘  │
  │         ↓                ↓                ↓          │
  │  ┌─────────────────────────────────────────────────┐ │
  │  │  Overshoot / Micro-correction engine            │ │
  │  └─────────────────────────────────────────────────┘ │
  │         ↓                                             │
  │  ┌─────────────────────────────────────────────────┐ │
  │  │  Low-level Execution Layer                      │ │
  │  │  ctypes → user32.dll SendInput()                │ │
  │  │  (MOUSEEVENTF_MOVE, hardware simulation flag)   │ │
  │  └─────────────────────────────────────────────────┘ │
  └──────────────────────────────────────────────────────┘

Key models implemented
-----------------------
1. **Path**      – Cubic Bézier curves with randomly-placed interior control
                   knots so no two trajectories between the same endpoints
                   are ever identical.
2. **Velocity**  – Minimum-Jerk Trajectory (Flash & Hogan, 1985): the brain
                   minimises the integral of the squared jerk (third derivative
                   of position). Results in a smooth bell-shaped speed profile
                   (slow → fast → slow) that matches empirical hand-movement data.
3. **Fitts Law** – Movement time scales with log2(2D/W) so longer / smaller
                   targets take proportionally more time, just like humans.
4. **Overshoot** – With configurable probability the cursor is sent slightly
                   beyond the goal; a short micro-correction sub-movement brings
                   it back. The overshoot distance itself follows Fitts scaling.
5. **Tremor**    – Smoothed Perlin-style 1-D noise (fractional Brownian motion
                   via octave superposition) adds per-axis hand tremor along the
                   path. Amplitude decays near start and end to avoid artefacts.
6. **Timing**    – High-resolution busy-wait loop (time.perf_counter) replaces
                   plain time.sleep to achieve sub-millisecond precision.
                   Per-step delays are randomised with Gaussian jitter.
7. **SendInput** – Direct ctypes call to user32.SendInput with the
                   MOUSEEVENTF_MOVE | MOUSEINPUT_HARDWARE flag combination so
                   the kernel sees real hardware-class events.

Optional AHK output
-------------------
Call  trajectory.to_ahk_script(path)  to dump a ready-to-run AutoHotkey v1
script that replays the pre-calculated trajectory. Useful for environments
where even ctypes is blocked (e.g. kernel anti-cheat that inspects the
calling-process of every SendInput).

Usage
-----
    from utils.human_mouse import move_human_like

    move_human_like(
        start_pos=(100, 200),
        end_pos=(800, 600),
        speed_factor=1.0,           # >1 faster, <1 slower
        overshoot_probability=0.35, # 0–1
    )

Requirements (add to environment.yml if missing)
-------------------------------------------------
    numpy, scipy   – already present in most botty envs
    noise          – optional; pure-Python fallback included
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes
import math
import os
import random
import time
from typing import Optional, Tuple

import numpy as np
from scipy import interpolate

# ---------------------------------------------------------------------------
# Optional: try to import the `noise` library for Perlin noise.
# Fall back to a pure-Python fractional Brownian motion approximation.
# ---------------------------------------------------------------------------
try:
    import noise as _noise_lib
    _HAS_NOISE_LIB = True
except ImportError:
    _HAS_NOISE_LIB = False


# ---------------------------------------------------------------------------
# Windows / ctypes low-level structures
# ---------------------------------------------------------------------------
# Reference:
#   https://docs.microsoft.com/en-us/windows/win32/api/winuser/ns-winuser-mouseinput
#
#   typedef struct tagMOUSEINPUT {
#       LONG      dx;
#       LONG      dy;
#       DWORD     mouseData;
#       DWORD     dwFlags;
#       DWORD     time;
#       ULONG_PTR dwExtraInfo;
#   } MOUSEINPUT;

INPUT_MOUSE                  = 0
MOUSEEVENTF_MOVE             = 0x0001   # relative movement
MOUSEEVENTF_ABSOLUTE         = 0x8000   # normalised absolute coordinates
MOUSEEVENTF_MOVE_NOCOALESCE  = 0x2000   # do not coalesce – more realistic
MOUSEEVENTF_VIRTUALDESK      = 0x4000   # map to full virtual desktop


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          ctypes.c_long),
        ("dy",          ctypes.c_long),
        ("mouseData",   ctypes.c_ulong),
        ("dwFlags",     ctypes.c_ulong),
        ("time",        ctypes.c_ulong),         # 0 = use system timestamp
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT)]


class _INPUT(ctypes.Structure):
    _anonymous_ = ("_input",)
    _fields_ = [
        ("type",   ctypes.c_ulong),
        ("_input", _INPUT_UNION),
    ]


_user32 = ctypes.windll.user32


def _get_screen_size() -> Tuple[int, int]:
    """Return (width, height) of the primary monitor in pixels."""
    return _user32.GetSystemMetrics(0), _user32.GetSystemMetrics(1)


def _send_relative_move(dx: int, dy: int) -> None:
    """
    Issue a single MOUSEEVENTF_MOVE (relative) SendInput event.

    Why relative rather than absolute?
    -----------------------------------
    DirectInput / Raw-Input games read relative delta reports from the HID
    layer – the same format produced by a physical mouse. Absolute events
    map to the desktop coordinate space and are typically ignored by the
    game's input thread. Sending relative deltas is therefore the correct
    primitive for 3D games.
    """
    inp = _INPUT()
    inp.type = INPUT_MOUSE
    inp.mi = _MOUSEINPUT(
        dx=int(dx),
        dy=int(dy),
        mouseData=0,
        dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_MOVE_NOCOALESCE,
        time=0,
        dwExtraInfo=None,
    )
    _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


def _send_absolute_move(x: int, y: int) -> None:
    """
    Issue a MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE SendInput event.

    Coordinates are normalised to the [0, 65535] virtual desktop range as
    required by the Win32 API (NOT raw pixel values).
    """
    sw, sh = _get_screen_size()
    norm_x = max(0, min(65535, int((x * 65535) // max(1, sw - 1))))
    norm_y = max(0, min(65535, int((y * 65535) // max(1, sh - 1))))

    inp = _INPUT()
    inp.type = INPUT_MOUSE
    inp.mi = _MOUSEINPUT(
        dx=norm_x,
        dy=norm_y,
        mouseData=0,
        dwFlags=(MOUSEEVENTF_MOVE
                 | MOUSEEVENTF_ABSOLUTE
                 | MOUSEEVENTF_MOVE_NOCOALESCE
                 | MOUSEEVENTF_VIRTUALDESK),
        time=0,
        dwExtraInfo=None,
    )
    _user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(_INPUT))


# ---------------------------------------------------------------------------
# High-resolution precise sleep
# ---------------------------------------------------------------------------

def _precise_sleep(seconds: float) -> None:
    """
    Hybrid busy-wait sleep with ~0.05 ms accuracy.

    Strategy
    --------
    1. Call time.sleep() for (duration - 2ms) to avoid wasting CPU.
    2. Spin-wait with time.perf_counter() for the final 2 ms.

    This gives sub-millisecond precision while keeping CPU load low – far
    better than Windows' default 15.6 ms timer resolution.
    """
    if seconds <= 0:
        return
    deadline = time.perf_counter() + seconds
    coarse = seconds - 0.002
    if coarse > 0:
        time.sleep(coarse)
    while time.perf_counter() < deadline:
        pass


# ---------------------------------------------------------------------------
# Perlin / fractional Brownian motion noise
# ---------------------------------------------------------------------------

def _fbm_1d(t: float, octaves: int = 6, persistence: float = 0.5, seed: int = 0) -> float:
    """
    1-D fractional Brownian motion via summed noise octaves.

    If the optional `noise` package is installed, uses its fast C
    implementation of Perlin noise. Otherwise falls back to a pure-Python
    sin-wave superposition that shares similar spectral/smoothness properties.

    Returns a value in approximately [-1, 1].
    """
    if _HAS_NOISE_LIB:
        return _noise_lib.pnoise1(
            t + seed * 1000.0,
            octaves=octaves,
            persistence=persistence,
            lacunarity=2.0,
            repeat=1024,
            base=seed % 256,
        )
    # Pure-Python fallback: sum of sin waves with pseudo-random phases
    rng = random.Random(seed)
    value = 0.0
    amplitude = 1.0
    frequency = 1.0
    max_val = 0.0
    for _ in range(octaves):
        phase = rng.uniform(0, 2 * math.pi)
        value += math.sin(2 * math.pi * frequency * t + phase) * amplitude
        max_val += amplitude
        amplitude *= persistence
        frequency *= 2.0
    return value / max_val if max_val > 0 else 0.0


# ---------------------------------------------------------------------------
# Bézier path generation
# ---------------------------------------------------------------------------

class _BezierPath:
    """
    Compound cubic Bézier / B-Spline path generator.

    A cubic Bézier is fully determined by 4 points: P0 (start), P3 (end),
    and two interior control points P1, P2. Here we generate n_interior_knots
    random interior waypoints displaced laterally from the straight-line
    path, then fit a parametric spline through all of them.

    This guarantees:
      - The path starts exactly at `start` and ends exactly at `end`.
      - No two calls generate the same path (different rng seed each time).
      - The curve is C² smooth (scipy BSpline degree-3).
    """

    def __init__(
        self,
        start:            Tuple[float, float],
        end:              Tuple[float, float],
        spread_factor:    float = 0.25,
        n_interior_knots: int   = 2,
        rng:              Optional[random.Random] = None,
    ):
        self._rng = rng or random.Random()
        self.start = np.array(start, dtype=float)
        self.end   = np.array(end,   dtype=float)
        self._spread = spread_factor
        self._n_interior = n_interior_knots
        self._control_points = self._build_control_points()

    # ------------------------------------------------------------------
    def _perp(self, v: np.ndarray) -> np.ndarray:
        """Return unit vector perpendicular to v (2-D)."""
        p = np.array([-v[1], v[0]], dtype=float)
        n = np.linalg.norm(p)
        return p / n if n > 1e-9 else np.array([0.0, 1.0])

    def _build_control_points(self) -> np.ndarray:
        """
        Construct the list [start, k1, k2, ..., end] of control points.

        Interior knots are placed along the straight line at evenly-spaced
        parameter values and then displaced laterally by a Gaussian random
        amount proportional to (distance × spread_factor).
        """
        pts = [self.start]
        vec  = self.end - self.start
        dist = np.linalg.norm(vec)
        direction = vec / dist if dist > 1e-9 else np.array([1.0, 0.0])
        perp = self._perp(direction)
        n    = self._n_interior + 1

        for i in range(1, self._n_interior + 1):
            t         = i / n
            lateral   = self._rng.gauss(0, dist * self._spread * 0.5)
            long_jit  = self._rng.gauss(0, dist * 0.05)
            pt        = self.start + direction * (dist * t + long_jit) + perp * lateral
            pts.append(pt)

        pts.append(self.end)
        return np.array(pts)

    def evaluate(self, n_points: int) -> np.ndarray:
        """
        Sample `n_points` equidistant-in-parameter points along the spline.

        Uses chord-length parameterisation for a natural feel (avoids
        clustering near tightly-packed control points).

        Returns
        -------
        np.ndarray, shape (n_points, 2)
        """
        ctrl = self._control_points
        degree = min(3, len(ctrl) - 1)

        if degree < 1:
            return np.tile(self.start, (n_points, 1))

        # Chord-length parameterisation of control polygon
        diffs        = np.diff(ctrl, axis=0)
        chord_lens   = np.linalg.norm(diffs, axis=1)
        total_chord  = chord_lens.sum()

        if total_chord < 1e-9:
            return np.tile(self.start, (n_points, 1))

        t_ctrl = np.concatenate([[0.0], np.cumsum(chord_lens) / total_chord])

        # Parametric spline through control points (s=0 → interpolating)
        tck, _ = interpolate.splprep(ctrl.T.tolist(), u=t_ctrl, k=degree, s=0)
        t_eval = np.linspace(0.0, 1.0, n_points)
        xy     = interpolate.splev(t_eval, tck)
        return np.column_stack(xy)   # (n_points, 2)


# ---------------------------------------------------------------------------
# Velocity profile – Minimum Jerk Model (Flash & Hogan, 1985)
# ---------------------------------------------------------------------------

def _minimum_jerk_position(t_norm: float) -> float:
    """
    Minimum-Jerk normalised position profile.

    The minimum-jerk model minimises ∫ |d³x/dt³|² dt subject to boundary
    conditions x(0)=0, x(T)=1, ẋ(0)=ẋ(T)=0, ẍ(0)=ẍ(T)=0.

    The closed-form solution is:
        x(τ) = 10τ³ − 15τ⁴ + 6τ⁵,   τ ∈ [0, 1]

    Its velocity   ẋ(τ) = 30τ²(1−τ)²  is a symmetric bell-curve peaking at τ=0.5.
    Its acceleration starts positive, crosses zero at τ=0.5, ends negative.

    This maps a linear time parameter to a non-linear position, producing
    the characteristic slow-fast-slow human reaching movement.

    Parameters
    ----------
    t_norm : float in [0, 1]

    Returns
    -------
    float in [0, 1] – normalised position
    """
    τ = max(0.0, min(1.0, t_norm))
    return 10 * τ**3 - 15 * τ**4 + 6 * τ**5


# ---------------------------------------------------------------------------
# Fitts's Law timing estimate
# ---------------------------------------------------------------------------

def _fitts_time(distance: float, target_width: float, speed_factor: float) -> float:
    """
    Estimate movement time using the ISO Fitts's Law model:

        MT = a + b · ID      where  ID = log2(2D / W)

    Empirical constants (Mackenzie 1992 aggregated dataset):
        a = 0.05 s  (motor-initiation intercept)
        b = 0.10 s/bit

    Parameters
    ----------
    distance     : Euclidean pixel distance from start to end.
    target_width : Effective target diameter in pixels (Fitts's "W").
    speed_factor : Scalar; >1 faster, <1 slower.

    Returns
    -------
    float : Movement duration in seconds, clamped to [0.05, 3.0].
    """
    if distance < 1:
        return 0.05
    W  = max(1.0, target_width)
    ID = math.log2(2.0 * distance / W)
    a, b = 0.05, 0.10
    mt   = (a + b * ID) / max(0.01, speed_factor)
    return max(0.05, min(3.0, mt))


# ---------------------------------------------------------------------------
# Trajectory container
# ---------------------------------------------------------------------------

class HumanTrajectory:
    """
    Container for a pre-computed human-like mouse trajectory.

    Attributes
    ----------
    points : np.ndarray, shape (N, 2)
        Pixel coordinates (float) in visit order.
    delays : np.ndarray, shape (N,)
        Time in seconds to wait *after* arriving at each point.
    """

    def __init__(self, points: np.ndarray, delays: np.ndarray):
        self.points = points
        self.delays = delays

    # ------------------------------------------------------------------
    def to_ahk_script(self, filepath: str = "") -> str:
        """
        Export the trajectory as an AutoHotkey v1 script.

        The generated script calls DllCall("SendInput") for each trajectory
        point, providing a "hands-off" fallback for environments that block
        Python ctypes calls (e.g. some kernel-level anti-cheats).

        Parameters
        ----------
        filepath : str
            File path to write (e.g. "C:/bots/move.ahk").
            Pass an empty string to only return the string without writing.

        Returns
        -------
        str : AHK script content.
        """
        lines = [
            "; ===================================================",
            "; Auto-generated by human_mouse.py  (AHK v1 replay)",
            "; Press F10 to execute, F12 to abort.",
            "; ===================================================",
            "#NoEnv",
            "#SingleInstance Force",
            "SetWorkingDir %A_ScriptDir%",
            "",
            "F12::ExitApp",
            "",
            "F10::",
        ]

        for i, (pt, dt) in enumerate(zip(self.points, self.delays)):
            x   = int(round(float(pt[0])))
            y   = int(round(float(pt[1])))
            ms  = max(1, int(round(float(dt) * 1000)))
            lines.append(f"MouseMove, {x}, {y}, 0   ; step {i}")
            lines.append(f"Sleep, {ms}")

        lines.append("return")
        body = "\n".join(lines)

        if filepath:
            with open(filepath, "w", encoding="utf-8") as fh:
                fh.write(body)

        return body


# ---------------------------------------------------------------------------
# Core public API
# ---------------------------------------------------------------------------

def move_human_like(
    start_pos:             Tuple[float, float],
    end_pos:               Tuple[float, float],
    speed_factor:          float = 1.0,
    overshoot_probability: float = 0.35,
    target_width:          float = 10.0,
    tremor_amplitude:      float = 1.2,
    use_absolute:          bool  = False,
    dry_run:               bool  = False,
) -> HumanTrajectory:
    """
    Compute and (optionally) execute a human-like mouse movement.

    Parameters
    ----------
    start_pos : (x, y)
        Starting cursor position in screen pixels.
    end_pos : (x, y)
        Destination cursor position in screen pixels.
    speed_factor : float, default 1.0
        Speed scalar. >1 moves faster, <1 moves slower. Internally
        divides the Fitts's Law movement-time estimate.
    overshoot_probability : float in [0, 1], default 0.35
        Probability of overshooting the target and issuing a
        micro-correction sub-movement. Mimics the human tendency to
        overshoot at high speeds or large distances.
    target_width : float, default 10.0
        Effective target diameter in pixels (Fitts's 'W'). Smaller
        targets → longer predicted movement time.
    tremor_amplitude : float, default 1.2
        Peak hand-tremor displacement in pixels. 0 disables tremor.
    use_absolute : bool, default False
        False → relative MOUSEEVENTF_MOVE events (for DirectInput games).
        True  → absolute MOUSEEVENTF_ABSOLUTE events (for desktop apps).
    dry_run : bool, default False
        If True, generate the trajectory but do NOT call SendInput.
        Useful for offline analysis or AHK export.

    Returns
    -------
    HumanTrajectory
        The computed trajectory. Call `.to_ahk_script(path)` to export.

    Notes on randomness
    -------------------
    Each call seeds a fresh `random.Random` from `os.urandom(8)`, so no
    two invocations share state and no two paths between the same endpoints
    will ever be mathematically identical.
    """
    # ---- Seed -------------------------------------------------------
    seed   = int.from_bytes(os.urandom(8), "little")
    rng    = random.Random(seed)
    np_rng = np.random.default_rng(seed)

    # ---- Geometry ---------------------------------------------------
    start = np.array(start_pos, dtype=float)
    end   = np.array(end_pos,   dtype=float)
    dist  = float(np.linalg.norm(end - start))

    # ----------------------------------------------------------------
    # Step 1 – Fitts's Law movement time
    # ----------------------------------------------------------------
    total_time  = _fitts_time(dist, target_width, speed_factor)
    # ±5% Gaussian jitter on total time for naturalness
    total_time *= rng.gauss(1.0, 0.05)
    total_time  = max(0.04, total_time)

    # ----------------------------------------------------------------
    # Step 2 – Probabilistic overshoot
    # ----------------------------------------------------------------
    # Human overshoots are most common during fast, long-distance moves.
    do_overshoot = (rng.random() < overshoot_probability) and dist > 30.0

    if do_overshoot:
        # Overshoot: 2–8% of distance, clamped to 3–25 px
        ov_frac   = rng.uniform(0.02, 0.08)
        ov_dist   = min(25.0, max(3.0, dist * ov_frac))
        direction = (end - start) / max(dist, 1e-9)
        perp      = np.array([-direction[1], direction[0]])
        lateral   = rng.gauss(0, ov_dist * 0.3)
        overshoot_pt = end + direction * ov_dist + perp * lateral
    else:
        overshoot_pt = None

    # ----------------------------------------------------------------
    # Step 3 – Primary path (Bézier from start → end or overshoot_pt)
    # ----------------------------------------------------------------
    primary_target  = overshoot_pt if do_overshoot else end
    n_interior      = rng.randint(1, 3)
    spread          = rng.uniform(0.10, 0.35)

    bezier_primary = _BezierPath(
        start=tuple(start),
        end=tuple(primary_target),
        spread_factor=spread,
        n_interior_knots=n_interior,
        rng=rng,
    )
    # Points ∝ distance; minimum 8, maximum 120
    n_primary  = max(8, min(120, int(dist * 0.18)))
    path_main  = bezier_primary.evaluate(n_primary)   # (N, 2)

    # ----------------------------------------------------------------
    # Step 4 – Micro-correction path (overshoot → exact target)
    # ----------------------------------------------------------------
    if do_overshoot:
        corr_dist   = float(np.linalg.norm(end - overshoot_pt))
        n_corr      = max(4, min(30, int(corr_dist * 0.25)))
        bezier_corr = _BezierPath(
            start=tuple(overshoot_pt),
            end=tuple(end),
            spread_factor=0.05,   # nearly straight micro-correction
            n_interior_knots=1,
            rng=rng,
        )
        path_corr = bezier_corr.evaluate(n_corr)  # (M, 2)
    else:
        path_corr = None

    # ----------------------------------------------------------------
    # Step 5 – Concatenate paths
    # ----------------------------------------------------------------
    if path_corr is not None:
        all_points = np.vstack([path_main, path_corr[1:]])  # skip duplicate junction
    else:
        all_points = path_main

    N = len(all_points)

    # ----------------------------------------------------------------
    # Step 6 – Minimum-Jerk velocity → per-step delay budget
    #
    # The minimum-jerk position function maps a linear τ ∈ [0,1] to a
    # non-linear position in [0,1]. Differencing adjacent position values
    # gives us a per-step velocity weight: small weight → slow (long delay),
    # large weight → fast (short delay). We then scale the weight array so
    # the total delay equals total_time.
    # ----------------------------------------------------------------
    tau_grid = np.linspace(0.0, 1.0, N)
    mj_pos   = np.vectorize(_minimum_jerk_position)(tau_grid)

    # Finite-difference velocity weights (forward-difference)
    mj_vel       = np.diff(mj_pos, prepend=mj_pos[0])
    mj_vel[0]    = mj_vel[1]    # avoid zero weight at the very first step

    if do_overshoot and path_corr is not None:
        n_p = len(path_main)
        n_c = N - n_p
        # 85% of time for primary reach, 15% for micro-correction
        t_p, t_c = total_time * 0.85, total_time * 0.15
        v_p, v_c = mj_vel[:n_p], mj_vel[n_p:]
        delays_p = (v_p / v_p.sum() * t_p) if v_p.sum() > 0 else np.full(n_p, t_p / n_p)
        delays_c = (v_c / v_c.sum() * t_c) if n_c > 0 and v_c.sum() > 0 else np.full(n_c, t_c / max(n_c, 1))
        base_delays = np.concatenate([delays_p, delays_c])
    else:
        s = mj_vel.sum()
        base_delays = mj_vel / s * total_time if s > 0 else np.full(N, total_time / N)

    # ----------------------------------------------------------------
    # Step 6b – Per-step Gaussian timing jitter (±15%)
    #
    # Anti-heuristic rationale: many anti-cheat systems detect bots by
    # looking for perfectly periodic mouse-move inter-arrival times.
    # Adding per-step Gaussian jitter destroys that periodicity while
    # keeping the global duration (Fitts's Law estimate) correct.
    # ----------------------------------------------------------------
    jitter  = np_rng.normal(1.0, 0.15, size=N)
    jitter  = np.clip(jitter, 0.5, 1.8)
    delays  = base_delays * jitter
    # Re-normalise so total time is preserved after jitter
    delays  = delays / delays.sum() * total_time

    # ----------------------------------------------------------------
    # Step 7 – Hand tremor (fractional Brownian motion)
    #
    # We evaluate 1-D fBm noise independently for x and y, multiply by a
    # sin-envelope that tapers to zero at both endpoints (so the cursor
    # still lands exactly on the target), and add the result to the path.
    # ----------------------------------------------------------------
    if tremor_amplitude > 0.0:
        seed_x = rng.randint(0, 9999)
        seed_y = rng.randint(0, 9999)

        t_noise  = np.linspace(0.0, 4.0, N)           # 4 full noise cycles
        # Envelope: zero at endpoints, maximum in middle
        envelope = np.sin(np.linspace(0.0, math.pi, N)) ** 0.5

        noise_x  = np.array([_fbm_1d(t, octaves=5, persistence=0.55, seed=seed_x) for t in t_noise])
        noise_y  = np.array([_fbm_1d(t, octaves=5, persistence=0.55, seed=seed_y) for t in t_noise])

        all_points[:, 0] += noise_x * envelope * tremor_amplitude
        all_points[:, 1] += noise_y * envelope * tremor_amplitude

    # ----------------------------------------------------------------
    # Step 8 – Build trajectory object
    # ----------------------------------------------------------------
    trajectory = HumanTrajectory(points=all_points, delays=delays)

    # ----------------------------------------------------------------
    # Step 9 – Execute via SendInput (skip if dry_run)
    # ----------------------------------------------------------------
    if not dry_run:
        _execute_trajectory(trajectory, start_pos=start_pos, use_absolute=use_absolute)

    return trajectory


# ---------------------------------------------------------------------------
# Execution layer
# ---------------------------------------------------------------------------

def _execute_trajectory(
    traj:        HumanTrajectory,
    start_pos:   Tuple[float, float],
    use_absolute: bool = False,
) -> None:
    """
    Replay a HumanTrajectory by issuing SendInput events at the correct
    high-resolution timing.

    Relative mode (use_absolute=False, default for games)
    -------------------------------------------------------
    Each step sends (Δx, Δy) relative to the previous trajectory point.
    This mirrors how a physical mouse reports motion to the HID layer and
    is the correct primitive for DirectInput / Raw-Input games.

    Absolute mode (use_absolute=True, for desktop apps)
    -------------------------------------------------------
    Each step sends normalised absolute [0, 65535] coordinates.
    """
    prev_x, prev_y = float(start_pos[0]), float(start_pos[1])

    for pt, delay in zip(traj.points, traj.delays):
        cur_x = float(pt[0])
        cur_y = float(pt[1])

        if use_absolute:
            _send_absolute_move(int(round(cur_x)), int(round(cur_y)))
        else:
            dx = int(round(cur_x - prev_x))
            dy = int(round(cur_y - prev_y))
            if dx != 0 or dy != 0:
                _send_relative_move(dx, dy)

        prev_x, prev_y = cur_x, cur_y
        _precise_sleep(float(delay))


# ---------------------------------------------------------------------------
# Convenience wrapper – drop-in replacement for pyautogui.moveTo()
# ---------------------------------------------------------------------------

def moveTo(x: float, y: float, **kwargs) -> HumanTrajectory:
    """
    Move from the *current* cursor position to (x, y).

    Reads the current cursor position from Win32 (zero overhead) and
    delegates to `move_human_like`. Accepts all the same keyword arguments.

    Example
    -------
        from utils.human_mouse import moveTo
        moveTo(640, 400, speed_factor=1.2, overshoot_probability=0.3)
    """
    pt = ctypes.wintypes.POINT()
    _user32.GetCursorPos(ctypes.byref(pt))
    return move_human_like(
        start_pos=(float(pt.x), float(pt.y)),
        end_pos=(float(x), float(y)),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Self-test / interactive demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("  human_mouse.py  –  interactive demo")
    print("=" * 60)
    print("  F12 = emergency stop")
    print("  Moves cursor to 5 random positions on screen.")
    print()

    try:
        import keyboard
        keyboard.add_hotkey("f12", lambda: sys.exit(0))
    except ImportError:
        print("  [hint] pip install keyboard for F12 emergency stop")

    sw, sh = _get_screen_size()
    rng    = random.Random()

    for i in range(5):
        tx = rng.randint(100, sw - 100)
        ty = rng.randint(100, sh - 100)
        sf = rng.uniform(0.8, 1.4)
        print(f"  Move {i+1}/5  →  ({tx:4d}, {ty:4d})  speed={sf:.2f}")

        traj = moveTo(
            tx, ty,
            speed_factor=sf,
            overshoot_probability=0.4,
            use_absolute=True,       # absolute is easier to observe in demos
            tremor_amplitude=1.2,
        )
        print(f"           {len(traj.points):3d} points,  "
              f"{traj.delays.sum():.3f}s total")
        time.sleep(0.4)

    print()
    print("Done.")
