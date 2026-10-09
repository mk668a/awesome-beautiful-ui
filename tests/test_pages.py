import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

spec = importlib.util.spec_from_file_location("pages", ROOT / "scripts" / "pages.py")
pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pages)

REPO = "owner/name"


def render(md, repo=REPO):
    return pages.Renderer(repo=repo).render(md)


class InlineTests(unittest.TestCase):
    def test_entry_line(self):
        out = render("- [Lenis](https://github.com/x/lenis) - Smooth scrolling. `★ 16k` `MIT` `2026-10`")
        self.assertEqual(
            out,
            '<ul><li><a href="https://github.com/x/lenis">Lenis</a> - Smooth scrolling. '
            "<code>★ 16k</code> <code>MIT</code> <code>2026-10</code></li></ul>",
        )

    def test_emphasis_and_escaping(self):
        self.assertEqual(render("**bold** and _em_ with <b> & 1 * 2"), "<p><strong>bold</strong> and <em>em</em> with &lt;b&gt; &amp; 1 * 2</p>")
        self.assertEqual(render("snake_case_name stays"), "<p>snake_case_name stays</p>")

    def test_code_span_is_not_parsed(self):
        self.assertEqual(render("`[not](a-link) **x**`"), "<p><code>[not](a-link) **x**</code></p>")

    def test_relative_links_point_at_github(self):
        out = render("[a](./list.json) [b](CONTRIBUTING.md#how) [c](./skills) [d](#contents) [e](https://e.io)")
        self.assertIn('href="https://github.com/owner/name/blob/main/list.json"', out)
        self.assertIn('href="https://github.com/owner/name/blob/main/CONTRIBUTING.md#how"', out)
        self.assertIn('href="https://github.com/owner/name/tree/main/skills"', out)
        self.assertIn('href="#contents"', out)
        self.assertIn('href="https://e.io"', out)

    def test_relative_links_untouched_without_repo(self):
        self.assertIn('href="./list.json"', render("[a](./list.json)", repo=None))

    def test_images_are_collected_as_assets(self):
        r = pages.Renderer(repo=REPO)
        out = r.render("![hero](./assets/hero.png) ![ext](https://x/y.png)")
        self.assertIn('<img src="assets/hero.png" alt="hero">', out)
        self.assertIn('<img src="https://x/y.png" alt="ext">', out)
        self.assertEqual(r.assets, ["assets/hero.png"])


    def test_entry_screenshots_render_and_are_collected(self):
        r = pages.Renderer(repo=REPO)
        out = r.render(
            "- [Lenis](https://github.com/x/lenis) - Smooth scrolling. `MIT`<br>\n"
            '  <img src="./assets/screenshots/x__lenis/1.webp" width="24%" alt="Lenis screenshot 1"> '
            '<img src="./assets/screenshots/x__lenis/2.webp" width="24%" alt="Lenis screenshot 2">\n'
            "- [Next](https://github.com/x/next) - Another. `MIT`"
        )
        self.assertIn(
            '<code>MIT</code><br> <a class="shot" href="assets/screenshots/x__lenis/1.webp">'
            '<img src="assets/screenshots/x__lenis/1.webp" alt="Lenis screenshot 1" loading="lazy"></a>', out)
        self.assertEqual(out.count("<li>"), 2)
        self.assertEqual(r.assets, ["assets/screenshots/x__lenis/1.webp", "assets/screenshots/x__lenis/2.webp"])

    def test_viewer_is_added_only_with_screenshots(self):
        shot = '- [A](https://a.example) text<br>\n  <img src="./assets/screenshots/a__b/1.webp" width="24%" alt="A screenshot 1">\n'
        self.assertIn('<dialog class="viewer"', pages.build("# T\n\n" + shot)[0])
        self.assertNotIn("<dialog", pages.build("# T\n\ntext\n")[0])

    def test_other_html_is_still_escaped(self):
        self.assertEqual(render("a <script>x</script>"), "<p>a &lt;script&gt;x&lt;/script&gt;</p>")


class BlockTests(unittest.TestCase):
    def test_heading_anchors_match_github(self):
        out = render("# Awesome Beautiful UI\n\n## Motion and text animation\n## WebGL & creative coding\n## Motion and text animation")
        self.assertIn('<h1 id="awesome-beautiful-ui">', out)
        self.assertIn('<h2 id="motion-and-text-animation">', out)
        self.assertIn('<h2 id="webgl--creative-coding">', out)
        self.assertIn('<h2 id="motion-and-text-animation-1">', out)

    def test_html_comments_are_dropped(self):
        out = render("<!-- LIST:START -->\n- a\n<!-- LIST:END -->")
        self.assertEqual(out, "<ul><li>a</li></ul>")

    def test_fenced_code_is_escaped(self):
        out = render("```sh\npython3 x.py <a> && b\n```")
        self.assertEqual(out, '<pre><code class="language-sh">python3 x.py &lt;a&gt; &amp;&amp; b</code></pre>')

    def test_blockquote(self):
        self.assertEqual(render("> Quoted **line**"), "<blockquote><p>Quoted <strong>line</strong></p></blockquote>")

    def test_table(self):
        out = render("| Step | Skill |\n|---|:-:|\n| 1 | `find` |\n")
        self.assertEqual(
            out,
            "<table><thead><tr><th>Step</th><th style=\"text-align:center\">Skill</th></tr></thead>"
            "<tbody><tr><td>1</td><td style=\"text-align:center\"><code>find</code></td></tr></tbody></table>",
        )

    def test_loose_ordered_list_with_nested_blocks(self):
        md = "1. First:\n\n   ```json\n   {}\n   ```\n\n   Trailing text.\n\n2. Second\n\n3. Third\n"
        out = render(md)
        self.assertEqual(out.count("<ol>"), 1)
        self.assertIn('<li>First:<pre><code class="language-json">{}</code></pre><p>Trailing text.</p></li>', out)
        self.assertIn("<li>Second</li><li>Third</li>", out)

    def test_paragraph_stops_at_list(self):
        out = render("Rules.\n1. one\n2. two")
        self.assertEqual(out, "<p>Rules.</p>\n<ol><li>one</li><li>two</li></ol>")


class BuildTests(unittest.TestCase):
    def test_page_title_and_description(self):
        page, assets = pages.build("# Title\n\n> One line.\n\n![x](./a.png)", repo=REPO)
        self.assertIn("<title>Title</title>", page)
        self.assertIn('<meta name="description" content="One line.">', page)
        self.assertIn("View on GitHub", page)
        self.assertEqual(assets, ["a.png"])

    def test_cli_writes_site_and_copies_assets(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "img").mkdir()
            (tmp / "img" / "a.png").write_bytes(b"png")
            (tmp / "README.md").write_text("# T\n\n![a](./img/a.png) ![missing](./img/b.png)", encoding="utf-8")
            out = tmp / "site"
            import subprocess, sys
            res = subprocess.run(
                [sys.executable, str(ROOT / "scripts" / "pages.py"), "--readme", str(tmp / "README.md"),
                 "--out", str(out), "--repo", REPO],
                capture_output=True, text=True,
            )
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertTrue((out / "index.html").is_file())
            self.assertTrue((out / ".nojekyll").is_file())
            self.assertEqual((out / "img" / "a.png").read_bytes(), b"png")
            self.assertFalse((out / "img" / "b.png").exists())
            self.assertIn("img/b.png: not found", res.stderr)


if __name__ == "__main__":
    unittest.main()
