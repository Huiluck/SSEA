import warnings, torch; warnings.filterwarnings("ignore")
from SSEA.fast_loop import FastLoop, STATE_SLEEP
from SSEA.environment import Environment
from SSEA.sse_protocols import FastLoopContext
import SSEA.fast_loop as fl

for seed in range(8):
    torch.manual_seed(seed)
    env = Environment(seed=seed)
    ctx = FastLoopContext(skills={}, rules={}, adapters={}, thresholds={}, retrieval={}, versions={})
    loop = FastLoop(environment=env, context=ctx)
    for t in range(400):
        rec = loop.step()
        if not env.alive: break
    notes = env.event_notes()
    gains = [n for n in notes if n[1] == "ENERGY_GAINED"]
    fails = [n for n in notes if n[1] == "ACTION_FAILED"]
    sleeps = sum(1 for r in loop.trace() if r.state == STATE_SLEEP)
    print(f"seed={seed} lived={t+1:3d} alive={env.alive!s:5s} sleeps={sleeps:2d} "
          f"energy_gained={len(gains):2d} action_failed={len(fails):3d} final_energy={env.energy:.3f}")
