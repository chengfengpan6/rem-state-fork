"""Run Chengfeng's frozen targeted plan on a subset of his 30 seeds with the Claude stand-in.
Usage: python run_claude_standin.py <rem-harness dir> <seeds comma-separated> <new output dir> [model] [effort] [resume-from interrupted run dir]"""
import sys, json, time
from pathlib import Path
HARNESS = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(HARNESS)); sys.path.insert(0, str(Path(__file__).resolve().parent))
from rem_harness.targeted import run_plan, read_json
from anthropic_provider import ClaudeProvider
from gemini_provider import GeminiProvider

def make_provider(model, effort):
    return GeminiProvider(model=model, effort=effort) if model.startswith("gemini") else ClaudeProvider(model=model, effort=effort)

seeds = [int(s) for s in sys.argv[2].split(",")]
out = Path(sys.argv[3]); model = sys.argv[4] if len(sys.argv) > 4 else "claude-opus-5-5"
effort = sys.argv[5] if len(sys.argv) > 5 else "low"
resume_from = Path(sys.argv[6]) if len(sys.argv) > 6 else None
cfg = read_json(HARNESS / "configs" / "targeted_30histories.json")
assert all(s in cfg["seeds"] for s in seeds), "seeds must come from the frozen selection"
cfg["seeds"] = seeds
cfg["expected_calls"] = 120 * len(seeds)
cfg["max_calls"] = min(3660, 120 * len(seeds) + 60)
providers = []
def factory():
    p = make_provider(model, effort); providers.append(p); return p
t0 = time.time()
result = run_plan(cfg, out, factory, workers=2, resume_from=resume_from)
usage = {"calls": 0, "input_tokens": 0, "output_tokens": 0, "cache_read_input_tokens": 0, "transport_retries": 0, "length_resamples": 0, "served_models": {}}
for p in providers:
    for k in ("calls", "input_tokens", "output_tokens", "cache_read_input_tokens", "transport_retries", "length_resamples"):
        usage[k] += p.usage[k]
    for m, n in p.usage["served_models"].items():
        usage["served_models"][m] = usage["served_models"].get(m, 0) + n
usage.update(model=model, effort=effort, seeds=seeds, wall_seconds=round(time.time() - t0),
             status=result["status"], error=result.get("error"))
(out / "standin_usage.json").write_text(json.dumps(usage, indent=2))
print(json.dumps(usage))
