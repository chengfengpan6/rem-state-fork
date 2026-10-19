"""Small explicit CLI; live calls require an explicit subcommand."""
import argparse
import json
from pathlib import Path

from .engine import Engine
from .models import default_config, expected_calls, validate_config
from .providers import CodexProvider, ReplayProvider


def main():
    parser = argparse.ArgumentParser(description="REM state-fork research prototype")
    parser.add_argument("mode", choices=["plan", "live", "replay"])
    parser.add_argument("--config")
    parser.add_argument("--output", default="runs/local")
    parser.add_argument("--recording", help="calls.jsonl or events.jsonl from the recorded run")
    parser.add_argument("--codex-bin", help="Official Codex executable; never an API key")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8")) if args.config else default_config()
    validate_config(config)
    if args.mode == "plan":
        print(json.dumps({"expected_calls": expected_calls(config), "config": config}, indent=2))
        return
    if args.mode == "live":
        if config["purpose"] != "smoke_noninferential" or config["formation_rounds"] > 3 or config["post_rounds"] > 3 or len(config["seeds"]) != 1:
            parser.error("This CLI permits only one seed and at most 3+3 rounds for live runs")
        provider = CodexProvider(args.codex_bin)
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
