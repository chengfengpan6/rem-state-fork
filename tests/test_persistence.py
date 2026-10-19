"""Offline regressions for bounded file replacement and failure reporting.

These inject filesystem failures; no live provider is constructed.
"""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from rem_harness import __main__ as cli
from rem_harness.engine import Engine
from rem_harness.models import default_config

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_core import FixtureProvider


class PersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_transient_replace_preserves_old_file_until_atomic_success(self):
        provider = FixtureProvider()
        engine = Engine(provider, default_config(), self.root)
        target = self.root / "checkpoint.json"
        old, new = {"generation": 1}, {"generation": 2}
        target.write_text(json.dumps(old), encoding="utf-8")
        original_replace = Path.replace
        attempts = []

        def locked_then_replace(source, destination):
            attempts.append(source.read_bytes())
            self.assertEqual(json.loads(target.read_text()), old)
            if len(attempts) < 5:
                raise PermissionError("temporary reader lock")
            return original_replace(source, destination)

        with patch.object(Path, "replace", new=locked_then_replace), \
                patch("rem_harness.engine.time.sleep") as sleep:
            engine._write_json("checkpoint.json", new)
        self.assertEqual(len(attempts), 5)
        self.assertEqual(len(set(attempts)), 1)  # Reuse one serialized file.
        self.assertEqual(json.loads(target.read_text()), new)
        self.assertFalse(target.with_suffix(".json.tmp").exists())
        self.assertEqual(sleep.call_count, 4)
        self.assertAlmostEqual(sum(c.args[0] for c in sleep.call_args_list), .5)
        self.assertEqual(provider.seen, [])

    def test_permanent_replace_stops_after_five_attempts_preserving_old_file(self):
        engine = Engine(FixtureProvider(), default_config(), self.root)
        target = self.root / "checkpoint.json"
        target.write_text('{"generation": 1}', encoding="utf-8")
        with patch.object(Path, "replace", side_effect=PermissionError("permanent lock")) as replace, \
                patch("rem_harness.engine.time.sleep") as sleep:
            with self.assertRaisesRegex(PermissionError, "permanent lock"):
                engine._write_json("checkpoint.json", {"generation": 2})
        self.assertEqual(replace.call_count, 5)
        self.assertEqual(sleep.call_count, 4)
        self.assertEqual(json.loads(target.read_text()), {"generation": 1})
        self.assertEqual(json.loads(target.with_suffix(".json.tmp").read_text()), {"generation": 2})

    def test_other_io_errors_are_not_retried(self):
        engine = Engine(FixtureProvider(), default_config(), self.root)
        with patch.object(Path, "replace", side_effect=OSError("disk failure")) as replace, \
                patch("rem_harness.engine.time.sleep") as sleep:
            with self.assertRaisesRegex(OSError, "disk failure"):
                engine._write_json("checkpoint.json", {})
        self.assertEqual(replace.call_count, 1)
        sleep.assert_not_called()

    def test_transient_checkpoint_lock_does_not_repeat_provider_calls(self):
        provider = FixtureProvider()
        output = self.root / "recovered"
        original_replace = Path.replace
        failures = []

        def transient_checkpoint_lock(source, destination):
            if Path(destination).name == "checkpoint.json" and len(provider.seen) == 9 and len(failures) < 2:
                failures.append(len(provider.seen))
                raise PermissionError("temporary checkpoint lock")
            return original_replace(source, destination)

        with patch.object(Path, "replace", new=transient_checkpoint_lock), \
                patch("rem_harness.engine.time.sleep"):
            result = Engine(provider, default_config(), output).run()
        self.assertEqual(result["status"], "completed", result["error"])
        self.assertEqual(failures, [9, 9])
        self.assertEqual(len(provider.seen), 342)
        self.assertEqual(result["calls_attempted"], 342)
        records = [json.loads(s) for s in (output / "calls.jsonl").read_text().splitlines()]
        requests = [r for r in records if r["event"] == "call_request"]
        self.assertEqual([r["call_id"] for r in requests], [f"call-{n:06d}" for n in range(1, 343)])

    def test_permanent_checkpoint_failure_stops_dispatch_and_saves_failure_summary(self):
        provider = FixtureProvider()
        output = self.root / "failed"
        original_replace = Path.replace
        failed_attempts = []

        def permanent_checkpoint_lock(source, destination):
            if Path(destination).name == "checkpoint.json" and len(provider.seen) >= 9:
                failed_attempts.append(len(provider.seen))
                raise PermissionError("checkpoint remains locked")
            return original_replace(source, destination)

        with patch.object(Path, "replace", new=permanent_checkpoint_lock), \
                patch("rem_harness.engine.time.sleep") as sleep:
            result = Engine(provider, default_config(), output).run()
        self.assertEqual(failed_attempts, [9] * 5)
        self.assertEqual(sleep.call_count, 4)
        self.assertEqual(len(provider.seen), 9)
        self.assertEqual(result["calls_attempted"], 9)
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], {"type": "PermissionError", "message": "checkpoint remains locked"})
        self.assertEqual(json.loads((output / "summary.json").read_text()), result)
        self.assertEqual(json.loads((output / "manifest.json").read_text())["status"], "error")
        self.assertEqual(json.loads((output / "checkpoint.json").read_text())["seeds"], {})

    def test_initial_checkpoint_failure_is_reported_before_any_dispatch(self):
        provider = FixtureProvider()
        output = self.root / "initial-failure"
        original_replace = Path.replace

        def locked(source, destination):
            if Path(destination).name == "checkpoint.json":
                raise PermissionError("initial checkpoint locked")
            return original_replace(source, destination)

        with patch.object(Path, "replace", new=locked), patch("rem_harness.engine.time.sleep") as sleep:
            result = Engine(provider, default_config(), output).run()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["type"], "PermissionError")
        self.assertEqual(result["calls_attempted"], 0)
        self.assertEqual(provider.seen, [])
        self.assertEqual(sleep.call_count, 4)
        self.assertEqual(json.loads((output / "summary.json").read_text()), result)

    def test_final_checkpoint_failure_preserves_original_provider_validation_error(self):
        class InvalidProvider(FixtureProvider):
            def complete(self, *args):
                self.seen.append(args)
                return {"probability": 1.1}

        provider = InvalidProvider()
        output = self.root / "two-errors"
        original_replace = Path.replace

        def locked_after_response(source, destination):
            if Path(destination).name == "checkpoint.json" and provider.seen:
                raise PermissionError("secondary checkpoint failure")
            return original_replace(source, destination)

        with patch.object(Path, "replace", new=locked_after_response), patch("rem_harness.engine.time.sleep"):
            result = Engine(provider, default_config(), output).run()
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"]["type"], "ValidationError")
        self.assertEqual(len(provider.seen), 1)
        records = [json.loads(s) for s in (output / "events.jsonl").read_text().splitlines()]
        self.assertTrue(any(r["event"] == "checkpoint_write_failed" for r in records))
        self.assertEqual(json.loads((output / "summary.json").read_text()), result)


class CliFailureTests(unittest.TestCase):
    def test_replay_failure_prints_original_error_before_nonzero_exit(self):
        failure = {"status": "error", "error": {"type": "PermissionError", "message": "original checkpoint error"}}
        provider = Mock(index=252, responses=[None] * 342)
        output = io.StringIO()
        with patch.object(sys, "argv", ["rem_harness", "replay", "--recording", "fixture.jsonl"]), \
                patch.object(cli, "ReplayProvider", return_value=provider), \
                patch.object(cli, "Engine") as engine, redirect_stdout(output):
            engine.return_value.run.return_value = failure
            with self.assertRaises(SystemExit) as stopped:
                cli.main()
        self.assertEqual(stopped.exception.code, 1)
        self.assertEqual(json.loads(output.getvalue()), failure)
        self.assertNotIn("unused responses", output.getvalue())

    def test_completed_replay_still_rejects_unused_responses(self):
        provider = Mock(index=341, responses=[None] * 342)
        with patch.object(sys, "argv", ["rem_harness", "replay", "--recording", "fixture.jsonl"]), \
                patch.object(cli, "ReplayProvider", return_value=provider), \
                patch.object(cli, "Engine") as engine, redirect_stdout(io.StringIO()):
            engine.return_value.run.return_value = {"status": "completed", "error": None}
            with self.assertRaisesRegex(RuntimeError, "Replay left unused responses"):
                cli.main()


if __name__ == "__main__":
    unittest.main()
