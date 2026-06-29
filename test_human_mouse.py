"""
Integration test: verifies custom_mouse.mouse.move() routes through
the human_mouse engine. Runs in dry-run mode -- no actual mouse movement.
"""
import sys
sys.path.insert(0, 'src')
import unittest.mock as mock

# Minimal stubs for heavy game-specific imports
sys.modules.setdefault('screen', mock.MagicMock())
sys.modules.setdefault('template_finder', mock.MagicMock())
sys.modules.setdefault('config', mock.MagicMock())
config_mock = sys.modules['config']
config_mock.Config.return_value.ui_roi = {
    'gold_btn': [0,0,1,1],
    'equipped_inventory_area': [0,0,1,1],
    'restricted_inventory_area': [0,0,1,1]
}

# Patch low-level mouse library
mouse_lib_mock = mock.MagicMock()
mouse_lib_mock.get_position.return_value = (100, 200)
sys.modules.setdefault('mouse', mouse_lib_mock)
sys.modules['mouse']._winmouse = mock.MagicMock()

# Patch utils.misc and logger
sys.modules.setdefault('utils.misc', mock.MagicMock())
sys.modules['utils.misc'].is_in_roi = lambda *a, **kw: False
sys.modules.setdefault('logger', mock.MagicMock())

# Intercept _human_move call inside custom_mouse to verify routing
import utils.human_mouse as _hm_module

call_log = []
_original_move = _hm_module.move_human_like

def _spy_move(**kwargs):
    call_log.append(kwargs)
    kwargs['dry_run'] = True
    return _original_move(**kwargs)

_hm_module.move_human_like = _spy_move
import utils.custom_mouse as cm
cm._human_move = _spy_move

# ------------------------------------------------------------------ Test 1
print("--- Test 1: mouse.move() routes through human_mouse engine ---")
cm.mouse.move(500, 400)
assert len(call_log) == 1, f"Expected 1 call, got {len(call_log)}"
c = call_log[0]
assert 'speed_factor' in c, "speed_factor not passed"
assert 'overshoot_probability' in c, "overshoot_probability not passed"
assert 'use_absolute' in c, "use_absolute not passed"
assert c['use_absolute'] == True, "use_absolute should be True"
print(f"  start_pos={c['start_pos']}, end_pos={c['end_pos']}")
print(f"  speed_factor={c['speed_factor']:.3f}, overshoot_prob={c['overshoot_probability']}")
print("[OK] Routed correctly through human_mouse engine")

# ------------------------------------------------------------------ Test 2
print()
print("--- Test 2: delay_factor=[0.1, 0.14] -> faster movement ---")
call_log.clear()
cm.mouse.move(600, 300, delay_factor=[0.1, 0.14])
sf_fast = call_log[0]['speed_factor']
print(f"  speed_factor for delay_factor=[0.1,0.14]: {sf_fast:.2f}")
assert sf_fast > 3.0, f"Fast delay_factor should give speed_factor > 3, got {sf_fast}"
print("[OK] Fast delay maps to high speed_factor")

# ------------------------------------------------------------------ Test 3
print()
print("--- Test 3: delay_factor=[0.9, 1.4] -> slower movement ---")
call_log.clear()
cm.mouse.move(300, 250, delay_factor=[0.9, 1.4])
sf_slow = call_log[0]['speed_factor']
print(f"  speed_factor for delay_factor=[0.9,1.4]: {sf_slow:.2f}")
assert sf_slow < 1.5, f"Slow delay_factor should give speed_factor < 1.5, got {sf_slow}"
print("[OK] Slow delay maps to low speed_factor")

# ------------------------------------------------------------------ Test 4
print()
print("--- Test 4: absolute=False resolves relative offset ---")
call_log.clear()
cm.mouse.move(-50, 30, absolute=False)
end = call_log[0]['end_pos']
start = call_log[0]['start_pos']
# start=(100,200), offset=(-50,30) -> target=(50,230), jitter randomize=5
assert abs(end[0] - 50) <= 6, f"Relative x wrong: {end[0]}"
assert abs(end[1] - 230) <= 6, f"Relative y wrong: {end[1]}"
print(f"  start={start}, offset=(-50,30), resolved end~={end}")
print("[OK] Relative offset resolved correctly")

# ------------------------------------------------------------------ Test 5
print()
print("--- Test 5: tuple randomize=(rx, ry) handled ---")
call_log.clear()
cm.mouse.move(400, 350, randomize=(20, 5))
tw = call_log[0]['target_width']
assert tw >= 4.0, f"target_width should be >= 4, got {tw}"
print(f"  target_width for randomize=(20,5): {tw}")
print("[OK] Tuple randomize handled, target_width computed")

# ------------------------------------------------------------------ Done
print()
print("=" * 55)
print("  ALL INTEGRATION TESTS PASSED")
print("=" * 55)
