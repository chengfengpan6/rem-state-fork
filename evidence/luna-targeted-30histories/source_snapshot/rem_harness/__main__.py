"""Small explicit CLI; live calls require an explicit subcommand."""
import argparse
import json
from pathlib import Path

from .engine import Engine
from .models import default_config, expected_calls, validate_config
from .providers import CodexProvider, ReplayProvider, PrefixResumeProvider


def main():
    parser = argparse.ArgumentParser(description="REM state-fork research prototype")
    parser.add_argument("mode", choices=["plan", "live", "replay", "resume"])
    parser.add_argument("--config")
    parser.add_argument("--output", default="runs/local")
    parser.add_argument("--recording", help="calls.jsonl or events.jsonl from the recorded run")
    parser.add_argument("--codex-bin", help="Official Codex executable; never an API key")
    args = parser.parse_args()
    if args.config:
        config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    elif args.mode == "resume" and args.recording:
        config = json.loads((Path(args.recording)/"manifest.json").read_text(encoding="utf-8"))["config"]
    else:
        config = default_config()
    validate_config(config)
    if args.mode == "plan":
        print(json.dumps({"expected_calls": expected_calls(config), "config": config}, indent=2))
        return
    if args.mode in ("live", "resume"):
        v2 = config["protocol_version"].startswith("rem-prototype-0.2")
        if config["purpose"] != "smoke_noninferential" or config["formation_rounds"] > 3 or config["post_rounds"] > (2 if v2 else 3) or len(config["seeds"]) != 1:
            parser.error("Live is limited to one seed, formation<=3, and post<=2 (v2) / <=3 (v1)")
        if v2 and (config["per_branch_call_cap"] > 20 or config["formation_call_cap"] > 32 or config["max_calls"] > 300):
            parser.error("V2 live caps: 20 attempts per branch, 32 shared formation, 300 total")
        provider = CodexProvider(args.codex_bin)
        if args.mode == "resume":
            if not v2 or not args.recording:
                parser.error("Resume requires a v2 interrupted run directory via --recording")
            provider = PrefixResumeProvider(args.recording, provider, config, output_dir=args.output)
    else:
        if not args.recording:
            parser.error("replay requires --recording")
        provider = ReplayProvider(args.recording)
    result = Engine(provider, config, Path(args.output)).run()
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["status"] != "completed":
        raise SystemExit(1)
    if args.mode == "replay" and provider.index != len(provider.responses):
        raise RuntimeError("Replay left unused responses")


if __name__ == "__main__":
    main()
