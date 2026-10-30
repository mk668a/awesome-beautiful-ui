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
    "sites": "skills/find-candidates/scripts/sites.py",
    "collect": "skills/research-candidates/scripts/collect_facts.py",
    "audit": "skills/audit-list/scripts/audit.py",
    "build": "scripts/build.py",
    "screenshots": "scripts/screenshots.py",
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
                               ("reject", "reject"), ("pending", "needs-research"), ("site", "include")):
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

    def test_maintainer_exclusion_rejects_any_case(self):
        excluded = next(r for r in self.config["rules"] if r["id"] == "on-topic")["value"][0]
        f = fixture()
        f["facts"]["repo"] = excluded.upper()
        verdict, failed = self.verdict(f)
        self.assertEqual(verdict, "reject")
        self.assertEqual([r["id"] for r in failed], ["on-topic"])

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
                self.assertEqual({e.get("repo") or e["url"] for e in json.loads(target.read_text())},
                                 {"example/include", "example/quiet", "https://example.com"})
            self.assertEqual(json.loads(out.read_text())["asOf"], "2026-10-09")


    def test_site_rules(self):
        cases = (
            ("pricing", "paid", "reject"),
            ("pricing", None, "needs-research"),
            ("openSource", True, "reject"),
            ("openSource", None, "needs-research"),
            ("lastUpdated", "2026-07-08", "quiet"),
            ("lastUpdated", "2026-07-09", "include"),
            ("lastUpdated", None, "needs-research"),
            ("lastUpdatedEvidence", [], "needs-research"),
            ("kind", "app", "reject"),
            ("genericCollection", True, "reject"),
        )
        for field, value, expected in cases:
            with self.subTest(field=field, value=value):
                f = fixture("site")
                f["research"][field] = value
                self.assertEqual(self.verdict(f)[0], expected)

    def test_site_skips_repository_rules(self):
        verdict, failed = self.verdict(fixture("site"))
        self.assertEqual((verdict, failed), ("include", []))
        f = fixture()
        f["research"]["pricing"] = "paid"
        self.assertEqual(self.verdict(f)[0], "include")

    def test_site_needs_a_valid_url(self):
        f = fixture("site")
        f["facts"]["url"] = "example.com"
        self.assertEqual(self.verdict(f)[0], "needs-research")

    def test_site_entry_goes_to_closed_section(self):
        self.assertEqual(self.judge.entry_for(fixture("site")), {
            "section": "closed", "url": "https://example.com", "name": "Example Kit",
            "note": "Animated components with a particle black hole cursor.",
            "pricing": "freemium", "updated": "2026-10-01"})


class RuntimeTests(unittest.TestCase):
    def test_sites_records_candidates_and_checks_canaries(self):
        sites = load("sites")
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            write_json(tmp / "queries.json", {"webCanaries": ["https://www.canary.dev/"], "queries": [
                {"id": "framer", "section": "components", "web": ["free framer components"]},
                {"id": "tui", "section": "terminal", "q": "topic:tui"}]})
            write_json(tmp / "list.json", [{"url": "https://listed.dev"}])
            write_json(tmp / "findings/site__seen.dev.json", {"url": "https://seen.dev", "facts": {"url": "https://seen.dev"}})
            common = ["--queries", str(tmp / "queries.json"), "--list", str(tmp / "list.json"),
                      "--findings", str(tmp / "findings"), "--out", str(tmp / "sites.json")]

            def run(*argv):
                out = io.StringIO()
                with patch.object(sys, "argv", ["sites", *argv, *common]), contextlib.redirect_stdout(out), \
                        contextlib.redirect_stderr(io.StringIO()):
                    try:
                        sites.main()
                        code = 0
                    except SystemExit as exit:
                        code = exit.code
                return code, out.getvalue()

            self.assertEqual(run("start"), (0, "framer\tfree framer components\n"))
            self.assertEqual(run("check")[0], 1)
            code, out = run("add", "--query", "framer", "https://www.new.dev/?ref=x", "https://listed.dev/",
                            "https://seen.dev", "https://github.com/a/b", "https://canary.dev")
            self.assertEqual([line.split("\t")[0] for line in out.splitlines()], ["new", "known", "known", "skip", "new"])
            data = json.loads((tmp / "sites.json").read_text())
            self.assertEqual([c["url"] for c in data["candidates"]], ["https://new.dev", "https://canary.dev"])
            self.assertEqual(run("check"), (0, "ok\thttps://canary.dev\tframer\n"))
            self.assertEqual(run("add", "--query", "tui", "https://x.dev")[0], 2)

    def test_collect_site_reads_page_metadata(self):
        collect = load("collect")
        self.assertEqual(collect.site_url("http://WWW.Example.com/kit/?a=1"), "https://example.com/kit")
        self.assertEqual(collect.site_slug("https://www.example.com/kit/"), "site__example.com_kit")

        class Response(io.BytesIO):
            status = 200
            def geturl(self):
                return "https://www.example.com/"
            def __enter__(self):
                return self
            def __exit__(self, *exc):
                return False

        page = (b'<html><head><title> Example\n Kit </title><meta name="description" content="Free components.">'
                b'<meta property="og:description" content="ignored"></head></html>')
        with patch.object(collect.urllib.request, "urlopen", return_value=Response(page)):
            facts, intro = collect.collect_site("https://www.example.com/")
        self.assertEqual((facts["found"], facts["url"], facts["title"], intro),
                         (True, "https://example.com", "Example Kit", "Free components."))
        error = urllib.error.HTTPError("https://example.com", 404, "gone", {}, None)
        with patch.object(collect.urllib.request, "urlopen", side_effect=error):
            facts, intro = collect.collect_site("https://example.com")
        self.assertEqual((facts["found"], facts["status"], intro), (False, 404, None))
        error = urllib.error.HTTPError("https://example.com", 429, "slow down", {}, None)
        with patch.object(collect.urllib.request, "urlopen", side_effect=error):
            self.assertIsNone(collect.collect_site("https://example.com")[0]["found"])
        with patch.object(collect.urllib.request, "urlopen", side_effect=urllib.error.URLError("no DNS")):
            facts, intro = collect.collect_site("https://example.com")
        self.assertEqual((facts["found"], facts["error"]), (None, "no DNS"))

    def test_build_lists_sites_without_github(self):
        build = load("build")
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            recent = date.today().isoformat()
            entries = [
                {"section": "closed", "url": "https://old.dev", "name": "Old", "note": "Old kit.", "pricing": "free", "updated": "2020-01-01"},
                {"section": "closed", "url": "https://kit.dev", "name": "Kit", "note": "A kit.", "pricing": "freemium", "updated": recent},
            ]
            write_json(tmp / "list.json", entries)
            write_json(tmp / "skills/judge-candidates/rules.json", {"rules": [{"id": "active", "value": 3}, {"id": "site-active", "value": 3}]})
            (tmp / "README.md").write_text("<!-- LIST:START -->\n<!-- LIST:END -->\n")
            with patch.object(build, "ROOT", tmp), patch.object(build, "_token", side_effect=AssertionError("token")), \
                    patch.object(sys, "argv", ["build"]), contextlib.redirect_stdout(io.StringIO()):
                build.main()
            text = (tmp / "README.md").read_text()
            self.assertIn("## Not open source", text)
            self.assertIn("- [Kit](https://kit.dev) - A kit. `freemium` `updated %s`" % recent[:7], text)
            self.assertLess(text.index("## Not open source"), text.index("## Quiet classics"))
            self.assertGreater(text.index("[Old]"), text.index("## Quiet classics"))
            for bad in ({"section": "motion", "url": "https://kit.dev", "name": "K", "note": "n.", "pricing": "free", "updated": recent},
                        {"section": "closed", "repo": "a/b", "name": "K", "note": "n."},
                        {"section": "closed", "url": "https://kit.dev", "name": "K", "note": "n."}):
                with self.subTest(entry=bad):
                    write_json(tmp / "list.json", [bad])
                    with patch.object(build, "ROOT", tmp), patch.object(sys, "argv", ["build"]), \
                            self.assertRaises(SystemExit):
                        build.main()

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
            self.assertNotIn("<img", text)

    def test_audit_reports_notes_that_differ_from_research(self):
        audit = load("audit")
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            write_json(tmp / "list.json", [
                {"section": "gems", "repo": "a/same", "name": "Same", "note": "Same note."},
                {"section": "gems", "repo": "a/drift", "name": "Drift", "note": "Old note."},
            ])
            write_json(tmp / "findings/a__same.json", {"repo": "a/same", "research": {"status": "done", "note": "Same note."}})
            write_json(tmp / "findings/a__drift.json", {"repo": "A/Drift", "research": {"status": "done", "note": "New note."}})
            repo = {"archived": False, "pushed_at": "2026-10-01T00:00:00Z", "license": {"spdx_id": "MIT"}}
            out = io.StringIO()
            with patch.object(audit, "_token", return_value=None), \
                    patch.object(audit, "gh", side_effect=lambda path, token: dict(repo, full_name=path.split("/repos/")[1])), \
                    patch.object(sys, "argv", ["audit", "--list", str(tmp / "list.json"), "--findings", str(tmp / "findings")]), \
                    contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()), \
                    self.assertRaises(SystemExit) as done:
                audit.main()
            self.assertEqual(done.exception.code, 1)
            self.assertEqual(out.getvalue(), "note-drift\ta/drift\tresearch says: New note.\n")

    def test_readme_images_keep_lasting_urls_only(self):
        shots = load("screenshots")
        signed = ("https://private-user-images.githubusercontent.com/7636626/356249575-"
                  "68dd9cc9-3182-49ee-b8d5-cd6301902b6e.jpg?jwt=abc&amp;x=1")
        html = ('<img src="%s"><img src="https://private-user-images.githubusercontent.com/1/x.png?jwt=abc">'
                '<img src="https://www.shieldcn.dev/github/stars/a/b.svg"><img src="https://repobeats.axiom.co/api/embed/1.svg">'
                '<img src="https://contrib-circles.vercel.app/a/b"><img src="https://example.com/demo.png">' % signed)
        with patch.object(shots, "gh", return_value=html):
            self.assertEqual(shots.readme_images("a/b", None), [
                "https://github.com/user-attachments/assets/68dd9cc9-3182-49ee-b8d5-cd6301902b6e",
                "https://example.com/demo.png",
            ])

    def test_build_adds_existing_screenshots_to_an_entry(self):
        build = load("build")
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            shots = tmp / "assets/screenshots/example__gem"
            shots.mkdir(parents=True)
            for name in ("2.webp", "1.webp", "sources.json"):
                (shots / name).write_bytes(b"")
            with patch.object(build, "ROOT", tmp):
                text = build.line({"repo": "Example/Gem", "full_name": "Example/Gem", "name": "A & B", "note": "Note.",
                                   "stars": 50, "license_tag": "MIT", "pushed": "2026-10-01"})
            head, images = text.split("<br>\n  ")
            self.assertTrue(head.endswith("`2026-10`"))
            self.assertEqual(
                images,
                '<img src="./assets/screenshots/example__gem/1.webp" width="24%" alt="A &amp; B screenshot 1"> '
                '<img src="./assets/screenshots/example__gem/2.webp" width="24%" alt="A &amp; B screenshot 2">')

    def test_client_packaging_is_synchronized(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/sync_plugin.py"), "--check"],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
