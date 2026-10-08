import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import urllib.error
from datetime import date
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/findings"
AS_OF = date(2026, 10, 9)
SCRIPTS = {
    "judge": "skills/judge-candidates/scripts/judge.py",
    "search": "skills/find-candidates/scripts/search.py",
    "collect": "skills/research-candidates/scripts/collect_facts.py",
    "audit": "skills/audit-list/scripts/audit.py",
    "build": "scripts/build.py",
}


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / SCRIPTS[name])
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fixture(name="include"):
    return json.loads((FIXTURES / (name + ".json")).read_text())


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


class JudgeTests(unittest.TestCase):
    def setUp(self):
        self.judge = load("judge")
        self.config = json.loads((ROOT / "skills/judge-candidates/rules.json").read_text())

    def verdict(self, finding, as_of=AS_OF):
        return self.judge.judge(finding, self.config["rules"], self.config["verdicts"], as_of)

    def test_fixture_verdicts(self):
        for name, expected in (("include", "include"), ("quiet", "quiet"),
                               ("reject", "reject"), ("pending", "needs-research")):
            with self.subTest(name=name):
                self.assertEqual(self.verdict(fixture(name))[0], expected)

    def test_missing_observation_is_not_rejection(self):
        for field in ("kind", "requiresHostedService", "genericCollection"):
            for value in (None, {}, [], 0):
                with self.subTest(field=field, value=value):
                    f = fixture()
                    f["research"][field] = value
                    self.assertEqual(self.verdict(f)[0], "needs-research")
            f = fixture()
            del f["research"][field]
            self.assertEqual(self.verdict(f)[0], "needs-research")

    def test_confirmed_disqualifier_still_rejects(self):
        f = fixture()
        f["research"]["requiresHostedService"] = True
        f["research"]["demoViewed"] = False
        self.assertEqual(self.verdict(f)[0], "reject")

    def test_unknown_license_needs_research(self):
        for license_name in (None, "", " unknown ", "NOASSERTION", "none", "N/A"):
            with self.subTest(license=license_name):
                f = fixture()
                f["research"]["license"] = license_name
                self.assertEqual(self.verdict(f)[0], "needs-research")

    def test_malformed_signature_lists_cannot_pass(self):
        for field in ("effects", "evidenceUrls"):
            for value in ([None], [False], [1], [{}], [" "], ["valid", None], "text", None):
                with self.subTest(field=field, value=value):
                    f = fixture()
                    f["research"]["signature"][field] = value
                    self.assertEqual(self.verdict(f)[0], "needs-research")

    def test_empty_effects_are_a_confirmed_rejection(self):
        f = fixture()
        f["research"]["signature"]["effects"] = []
        self.assertEqual(self.verdict(f)[0], "reject")

    def test_evidence_requires_http_url(self):
        for value in ([], ["not a URL"], ["file:///tmp/demo"], ["https://"], ["https://[broken"]):
            with self.subTest(value=value):
                f = fixture()
                f["research"]["signature"]["evidenceUrls"] = value
                self.assertEqual(self.verdict(f)[0], "needs-research")

    def test_unverified_observations_block_inclusion(self):
        f = fixture()
        f["research"]["unverified"] = ["Hosted dependency inferred from README."]
        self.assertEqual(self.verdict(f)[0], "needs-research")

    def test_dates_and_activity_boundary(self):
        for pushed, expected in (("2026-07-09", "include"), ("2026-07-08", "quiet"),
                                 ("2026-02-30", "needs-research"), ("garbage", "needs-research"),
                                 ("2027-01-01", "needs-research")):
            with self.subTest(pushed=pushed):
                f = fixture()
                f["facts"]["pushed"] = pushed
                self.assertEqual(self.verdict(f)[0], expected)
        self.assertEqual(self.judge.months_ago(1, date(2024, 3, 31)), date(2024, 2, 29))
        self.assertEqual(self.judge.months_ago(1, date(2025, 3, 31)), date(2025, 2, 28))

    def test_as_of_is_reproducible(self):
        f = fixture()
        self.assertEqual(self.verdict(f, date(2026, 10, 9))[0], "include")
        self.assertEqual(self.verdict(f, date(2027, 2, 1))[0], "quiet")

    def test_note_boundaries_include_final_period(self):
        for length, expected in ((9, "needs-research"), (10, "include"),
                                 (160, "include"), (161, "needs-research")):
            f = fixture()
            f["research"]["note"] = "a" * (length - 1) + "."
            self.assertEqual(self.verdict(f)[0], expected)
        f["research"]["note"] = "An otherwise valid note.\n"
        self.assertEqual(self.verdict(f)[0], "needs-research")

    def test_missing_repo_cannot_be_applied(self):
        f = fixture()
        del f["facts"]["repo"]
        self.assertEqual(self.verdict(f)[0], "needs-research")

    def test_apply_only_passed_entries_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            target = tmp / "list.json"
            write_json(target, [])
            out = tmp / "nested/verdicts.json"
            command = [sys.executable, str(ROOT / SCRIPTS["judge"]), "--findings", str(FIXTURES),
                       "--out", str(out), "--list", str(target), "--as-of", AS_OF.isoformat(), "--apply"]
            for _ in range(2):
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual({e["repo"] for e in json.loads(target.read_text())},
                                 {"example/include", "example/quiet"})
            self.assertEqual(json.loads(out.read_text())["asOf"], "2026-10-09")


class RuntimeTests(unittest.TestCase):
    def test_github_404_is_missing_but_other_errors_stop(self):
        for name in ("search", "collect", "audit", "build"):
            module = load(name)
            for status in (404, 403, 500):
                with self.subTest(name=name, status=status):
                    error = urllib.error.HTTPError("https://api.github.com/repos/example/test", status,
                                                   "test response", {}, None)
                    with patch.object(module.urllib.request, "urlopen", side_effect=error) as request:
                        if status == 404:
                            self.assertIsNone(module.gh("/repos/example/test", "test-token"))
                        else:
                            with self.assertRaises(SystemExit):
                                module.gh("/repos/example/test", "test-token")
                    self.assertEqual(request.call_args.args[0].get_header("Authorization"), "Bearer test-token")

    def test_imports_do_not_access_credentials_or_network(self):
        with patch("subprocess.run", side_effect=AssertionError("credential access during import")), \
                patch("urllib.request.urlopen", side_effect=AssertionError("network during import")):
            for name in SCRIPTS:
                with self.subTest(name=name):
                    load(name)

    def test_help_needs_no_token_or_gh(self):
        env = dict(os.environ)
        env.pop("GITHUB_TOKEN", None)
        env.pop("GH_TOKEN", None)
        env["PATH"] = ""
        for path in SCRIPTS.values():
            with self.subTest(path=path):
                result = subprocess.run([sys.executable, str(ROOT / path), "--help"],
                                        env=env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("usage:", result.stdout.lower())

    def test_search_excludes_all_findings_and_aliases(self):
        search = load("search")
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            write_json(tmp / "list.json", [{"repo": "example/listed"}])
            for name in ("reject", "pending"):
                f = fixture(name)
                f["facts"]["movedFrom"] = "old/" + name
                write_json(tmp / "findings" / (name + ".json"), f)
            names = ["example/listed", "EXAMPLE/REJECT", "example/pending", "old/reject", "example/new"]
            items = [{"full_name": name, "name": name.split("/")[1], "stargazers_count": 500,
                      "created_at": "2026-09-01", "pushed_at": "2026-10-01"} for name in names]
            args = ["search", "--list", str(tmp / "list.json"), "--findings", str(tmp / "findings"),
                    "--out", str(tmp / "candidates.json"), "--only", "text-animation"]
            with patch.object(sys, "argv", args), patch.object(search, "_token", return_value="test"), \
                    patch.object(search, "gh", return_value={"items": items}) as gh, \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                search.main()
            self.assertIn("order=asc", gh.call_args.args[0])
            self.assertEqual([c["repo"] for c in json.loads((tmp / "candidates.json").read_text())["candidates"]],
                             ["example/new"])

    def test_collection_limit_prioritizes_low_stars_and_can_reset(self):
        collect = load("collect")
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            write_json(tmp / "candidates.json", {"candidates": [
                {"repo": "example/popular", "stars": 10000}, {"repo": "example/gem", "stars": 50}]})
            existing = fixture()
            existing["facts"]["repo"] = "example/gem"
            target = tmp / "findings/example__gem.json"
            write_json(target, existing)
            args = ["collect", "--candidates", str(tmp / "candidates.json"), "--limit", "1", "--out", str(tmp / "findings")]
            for reset in (False, True):
                with patch.object(sys, "argv", args + (["--reset-research"] if reset else [])), \
                        patch.object(collect, "_token", return_value="test"), \
                        patch.object(collect, "collect", return_value=(existing["facts"], "README")) as fetch, \
                        contextlib.redirect_stdout(io.StringIO()):
                    collect.main()
                fetch.assert_called_once_with("example/gem", "test")
                result = json.loads(target.read_text())
                self.assertEqual(result["research"]["status"], "pending" if reset else "done")

    def test_build_skips_404_and_keeps_source_list(self):
        build = load("build")
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            entries = [{"repo": "example/" + name, "section": "motion", "name": name, "note": "Some animation."}
                       for name in ("missing", "available")]
            write_json(tmp / "list.json", entries)
            write_json(tmp / "skills/judge-candidates/rules.json", {"rules": [{"id": "active", "value": 3}]})
            (tmp / "README.md").write_text("Before\n<!-- LIST:START -->\nold\n<!-- LIST:END -->\nAfter\n")
            def gh(path, token):
                if path.endswith("missing"):
                    return None
                return {"full_name": "example/available", "stargazers_count": 50, "archived": False,
                        "pushed_at": date.today().isoformat(), "license": {"spdx_id": "MIT"}}
            errors = io.StringIO()
            with patch.object(build, "ROOT", tmp), patch.object(build, "_token", return_value="test"), \
                    patch.object(build, "gh", side_effect=gh), patch.object(sys, "argv", ["build"]), \
                    contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(errors):
                build.main()
            text = (tmp / "README.md").read_text()
            self.assertIn("example/available", text)
            self.assertNotIn("example/missing", text)
            self.assertIn("1 unavailable", text)
            self.assertIn("example/missing", errors.getvalue())
            self.assertEqual(json.loads((tmp / "list.json").read_text()), entries)
            self.assertTrue(text.startswith("Before\n"))
            self.assertTrue(text.endswith("After\n"))

    def test_client_packaging_is_synchronized(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/sync_plugin.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
