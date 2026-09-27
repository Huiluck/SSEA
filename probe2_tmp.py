import warnings, torch; warnings.filterwarnings("ignore")
from SSEA.fast_loop import FastLoop
from SSEA.environment import Environment
from SSEA.sse_protocols import FastLoopContext

OPS = ("none","grasp","push","pull","use_tool","release")
print(f"{'seed':>4} {'manip_gate':>10} {'mem_gate':>9} | emitted operations           | min resource dist during run")
for seed in range(8):
    torch.manual_seed(seed)
    env = Environment(seed=seed)
    ctx = FastLoopContext(skills={}, rules={}, adapters={}, thresholds={}, retrieval={}, versions={})
    loop = FastLoop(environment=env, context=ctx)
    ops, mind = [], 99.0
    for t in range(70):
        rec = loop.step()
        a = rec.executed_action
        if a.manipulation: ops.append(a.manipulation.operation)
        for o, d in env.visible_objects():
            if o.kind == "resource": mind = min(mind, d)
        if not env.alive: break
    gv = {n: float(torch.sigmoid(l(loop.hidden))) for n, l in loop.decoder.gates.items()}
    cnt = {o: ops.count(o) for o in OPS if ops.count(o)}
    print(f"{seed:>4} {gv['manipulation']:>10.3f} {gv['memory']:>9.3f} | {str(cnt):29s} | {mind:.2f}")
