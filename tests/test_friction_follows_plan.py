"""Unit test for patches/01-friction-follows-plan.patch.

Runs against an installed sunnypilot tree (it imports openpilot.*), loading the PATCHED file under a separate module
name so the installed copy is not touched:

  PYTHONPATH=/data/openpilot:/data/openpilot/openpilot /usr/local/venv/bin/python test_friction_follows_plan.py \
      /path/to/patched/latcontrol_torque_ext_base.py
"""
import importlib.util, sys, types
import numpy as np

spec = importlib.util.spec_from_file_location("ext_base_patched", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
from openpilot.selfdrive.modeld.constants import ModelConstants
from opendbc.car.lateral import FRICTION_THRESHOLD
from opendbc.sunnypilot.car.lateral_ext import get_friction

GAIN, DB = m.RAV4_FRICTION_JERK_GAIN, m.RAV4_FRICTION_JERK_DEADBAND
fails = 0
def check(name, ok):
  global fails; fails += not ok; print(("PASS " if ok else "FAIL ") + name)

def make():
  o = object.__new__(m.LatControlTorqueExtBase)
  o.lat_jerk_friction_factor = 0.4; o.lat_accel_friction_factor = 1.0
  o.lookahead_lateral_jerk = 0.0; o.short_lateral_jerk = 0.0
  o.friction_look_ahead_v = [1.4, 2.0]; o.friction_look_ahead_bp = [9.0, 30.0]
  o.t_diffs = np.diff(ModelConstants.T_IDXS); o.desired_lat_jerk_time = 0.3
  return o

class Plan:  # stand-in for modelV2
  def __init__(self, y): self.acceleration = types.SimpleNamespace(y=list(y)); self.orientation = types.SimpleNamespace(x=[0.0] * 33)
CS = types.SimpleNamespace(vEgo=20.0, steeringRateDeg=0.0)
VM = types.SimpleNamespace(calc_curvature=lambda a, v, r: 0.0)
T = np.array(ModelConstants.T_IDXS)
p = make()

check(f"constants: gain {GAIN}, deadband {DB}", (GAIN, DB) == (0.5, 0.1))

# 1. the tracking error never matters (bumps don't get a friction push)
for err in (-1.5, -0.2, 0.0, 0.3, 1.5):
  p.short_lateral_jerk = 0.0
  check(f"steady plan, error {err:+.1f}: friction input 0", p.update_friction_input(err, 0.0) == 0.0)
  p.short_lateral_jerk = 0.6
  check(f"plan jerk +0.6, error {err:+.1f}: input {p.update_friction_input(err, 0.0):+.3f} == {GAIN*0.5:+.3f}",
        abs(p.update_friction_input(err, 0.0) - GAIN * 0.5) < 1e-12)

# 2. deadband and sign
for j, want in ((0.05, 0.0), (-0.1, 0.0), (0.3, GAIN * 0.2), (-0.3, -GAIN * 0.2), (1.0, GAIN * 0.9), (-2.0, -GAIN * 1.9)):
  p.short_lateral_jerk = j
  got = p.update_friction_input(0.0, 0.0)
  check(f"plan jerk {j:+.2f}: input {got:+.3f} (want {want:+.3f})", abs(got - want) < 1e-12)

# 3. torque push with the slider at 0.10: full push at 0.1 + 0.2/0.5 = 0.5 m/s^3
tp = types.SimpleNamespace(friction=0.10)
for j, want in ((0.0, 0.0), (0.1, 0.0), (0.3, 0.05), (0.5, 0.10), (2.0, 0.10), (-0.5, -0.10)):
  p.short_lateral_jerk = j
  got = get_friction(p.update_friction_input(0.0, 0.0), 0.0, FRICTION_THRESHOLD, tp)
  check(f"slider 0.10, plan jerk {j:+.1f}: torque push {got:+.3f} (want {want:+.3f})", abs(got - want) < 1e-9)

# 4. short-range jerk from the model: plan reaching +0.3 m/s^2 more in 0.3 s -> +1.0 m/s^3, even if it reverses later
for label, y, want in (("unwind then reverse", np.where(T < 1.0, -1.4 + 1.0 * T, -0.4 - 0.5 * (T - 1.0)), 1.0),
                       ("steady", np.full(33, -1.2), 0.0), ("falling", 0.2 - 0.5 * T, -0.5)):
  p.model_v2 = Plan(y); p.model_valid = True
  p.update_calculations(CS, VM, float(y[0]))
  check(f"{label} plan: short jerk {p.short_lateral_jerk:+.3f} (want {want:+.3f}); stock look-ahead {p.lookahead_lateral_jerk:+.3f}",
        abs(p.short_lateral_jerk - want) < 1e-6)

# 5. no valid model -> no push
p.model_valid = False; p.update_calculations(CS, VM, 0.0)
check("model invalid: short jerk 0", p.short_lateral_jerk == 0.0 and p.update_friction_input(1.0, 0.0) == 0.0)

print(f"\n{fails} failure(s)"); sys.exit(1 if fails else 0)
