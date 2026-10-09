#!/usr/bin/env python3
"""Converts README.md into a single-file HTML page for GitHub Pages.

Usage: python3 scripts/pages.py [--out site] [--readme README.md] [--repo owner/name]

Standard library only. Relative links in the README (./list.json, CONTRIBUTING.md)
are rewritten to the GitHub repository so they keep working on the published page.
"""

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FENCE = re.compile(r"^(```|~~~)\s*([\w+-]*)\s*$")
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
BULLET = re.compile(r"^(\s*)[-*+]\s+(.*)$")
NUMBERED = re.compile(r"^(\s*)\d+[.)]\s+(.*)$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?\s*$")
RULE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")
COMMENT = re.compile(r"<!--.*?-->", re.S)
INLINE = re.compile(
    r"(?P<code>`+)(?P<code_text>.+?)(?P=code)"
    r"|!\[(?P<img_alt>[^\]]*)\]\((?P<img_src>[^)\s]+)(?:\s+\"[^\"]*\")?\)"
    r"|\[(?P<link_text>[^\]]+)\]\((?P<link_href>[^)\s]+)(?:\s+\"[^\"]*\")?\)"
    r"|\*\*(?P<bold>.+?)\*\*"
    r"|(?<![\w*])\*(?!\s)(?P<em_star>.+?)(?<!\s)\*(?![\w*])"
    r"|(?<!\w)_(?!\s)(?P<em_under>.+?)(?<!\s)_(?!\w)"
    r"|<(?P<auto>https?://[^>\s]+)>"
    r"|(?P<br><br\s*/?>)"
    r"|<img\s(?P<html_img>[^<>]*)>"
)
ATTR = re.compile(r'([\w-]+)="([^"]*)"')


def repo_slug(explicit):
    """owner/name of the GitHub repository, used to resolve relative links."""
    if explicit:
        return explicit
    env = os.environ.get("GITHUB_REPOSITORY")
    if env:
        return env
    try:
        manifest = json.loads((ROOT / "plugin.json").read_text(encoding="utf-8"))
        m = re.search(r"github\.com/([^/]+/[^/]+?)(?:\.git)?/?$", manifest.get("repository", ""))
        if m:
            return m.group(1)
    except (OSError, ValueError):
        pass
    try:
        url = subprocess.run(
            ["git", "-C", str(ROOT), "remote", "get-url", "origin"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?$", url)
        if m:
            return m.group(1)
    except (OSError, subprocess.CalledProcessError):
        pass
    return None


class Renderer:
    def __init__(self, repo=None, branch="main"):
        self.repo = repo
        self.branch = branch
        self.slugs = {}
        self.title = None
        self.headings = []
        self.assets = []  # relative image paths to copy next to index.html

    # ---- links -------------------------------------------------------------

    def href(self, url):
        """Rewrite README-relative links to the repository on GitHub."""
        if url.startswith(("#", "http://", "https://", "mailto:", "//")):
            return url
        if not self.repo:
            return url
        path = url[2:] if url.startswith("./") else url
        path, _, fragment = path.partition("#")
        kind = "tree" if path.endswith("/") or "." not in path.rsplit("/", 1)[-1] else "blob"
        out = "https://github.com/%s/%s/%s/%s" % (self.repo, kind, self.branch, path.strip("/"))
        return out + ("#" + fragment if fragment else "")

    def src(self, url):
        """Images in the repository are copied into the site, so they stay relative."""
        if url.startswith(("http://", "https://", "data:", "//")):
            return url
        path = (url[2:] if url.startswith("./") else url).lstrip("/")
        self.assets.append(path)
        return path

    def slug(self, text):
        """GitHub-style heading anchor: lowercase, punctuation removed, spaces to hyphens."""
        plain = re.sub(r"<[^>]+>", "", text)
        plain = html.unescape(plain).lower().strip()
        plain = re.sub(r"[^\w\- ]", "", plain).replace(" ", "-")
        n = self.slugs.get(plain, 0)
        self.slugs[plain] = n + 1
        return plain if n == 0 else "%s-%d" % (plain, n)

    # ---- inline ------------------------------------------------------------

    def inline(self, text):
        out = []
        pos = 0
        for m in INLINE.finditer(text):
            out.append(html.escape(text[pos:m.start()], quote=False))
            pos = m.end()
            g = m.groupdict()
            if g["code"]:
                out.append("<code>%s</code>" % html.escape(g["code_text"].strip(), quote=False))
            elif g["img_src"]:
                out.append('<img src="%s" alt="%s">' % (html.escape(self.src(g["img_src"])), html.escape(g["img_alt"])))
            elif g["link_href"]:
                out.append('<a href="%s">%s</a>' % (html.escape(self.href(g["link_href"])), self.inline(g["link_text"])))
            elif g["bold"]:
                out.append("<strong>%s</strong>" % self.inline(g["bold"]))
            elif g["em_star"] or g["em_under"]:
                out.append("<em>%s</em>" % self.inline(g["em_star"] or g["em_under"]))
            elif g["br"]:
                out.append("<br>")
            elif g["html_img"]:
                # The screenshot rows of the list are HTML because Markdown cannot size an image.
                attrs = dict(ATTR.findall(g["html_img"]))
                src = html.escape(self.src(html.unescape(attrs.get("src", ""))))
                out.append('<a class="shot" href="%s"><img src="%s" alt="%s" loading="lazy"></a>' % (
                    src, src, html.escape(html.unescape(attrs.get("alt", "")))))
            elif g["auto"]:
                out.append('<a href="%s">%s</a>' % (html.escape(g["auto"]), html.escape(g["auto"])))
        out.append(html.escape(text[pos:], quote=False))
        return "".join(out)

    # ---- blocks ------------------------------------------------------------

    def blocks(self, lines):
        out = []
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            if not line.strip():
                i += 1
                continue

            fence = FENCE.match(line)
            if fence:
                marker, lang = fence.groups()
                body = []
                i += 1
                while i < n and not lines[i].startswith(marker):
                    body.append(lines[i])
                    i += 1
                i += 1  # closing fence
                cls = ' class="language-%s"' % html.escape(lang) if lang else ""
                out.append("<pre><code%s>%s</code></pre>" % (cls, html.escape("\n".join(body), quote=False)))
                continue

            heading = HEADING.match(line)
            if heading:
                level = len(heading.group(1))
                text = self.inline(heading.group(2))
                anchor = self.slug(heading.group(2))
                if level == 1 and self.title is None:
                    self.title = html.unescape(re.sub(r"<[^>]+>", "", text))
                self.headings.append((level, anchor, text))
                out.append('<h%d id="%s">%s</h%d>' % (level, anchor, text, level))
                i += 1
                continue

            if RULE.match(line):
                out.append("<hr>")
                i += 1
                continue

            if line.lstrip().startswith(">"):
                body = []
                while i < n and lines[i].lstrip().startswith(">"):
                    body.append(re.sub(r"^\s*> ?", "", lines[i]))
                    i += 1
                out.append("<blockquote>%s</blockquote>" % "".join(self.blocks(body)))
                continue

            if "|" in line and i + 1 < n and TABLE_SEP.match(lines[i + 1]) and "|" in lines[i + 1]:
                out.append(self.table(lines, i))
                while i < n and lines[i].strip():
                    i += 1
                continue

            if BULLET.match(line) or NUMBERED.match(line):
                block, i = self.list(lines, i)
                out.append(block)
                continue

            if line.startswith("<") and not line.startswith("<!--"):
                body = []
                while i < n and lines[i].strip():
                    body.append(lines[i])
                    i += 1
                out.append("\n".join(body))
                continue

            body = []
            while i < n and lines[i].strip() and not self.starts_block(lines, i):
                body.append(lines[i].strip())
                i += 1
            out.append("<p>%s</p>" % self.inline(" ".join(body)))
        return out

    def starts_block(self, lines, i):
        line = lines[i]
        return bool(
            FENCE.match(line) or HEADING.match(line) or RULE.match(line)
            or line.lstrip().startswith(">") or BULLET.match(line) or NUMBERED.match(line)
            or ("|" in line and i + 1 < len(lines) and TABLE_SEP.match(lines[i + 1]))
        )

    def list(self, lines, i):
        first = BULLET.match(lines[i]) or NUMBERED.match(lines[i])
        ordered = NUMBERED.match(lines[i]) is not None
        pattern = NUMBERED if ordered else BULLET
        indent = len(first.group(1))
        items = []
        n = len(lines)
        while i < n:
            m = pattern.match(lines[i])
            if not m or len(m.group(1)) != indent:
                break
            item = [m.group(2)]
            i += 1
            # Continuation: indented lines (and blank lines leading to one) belong to this item.
            while i < n:
                nxt = lines[i]
                if not nxt.strip():
                    j = i
                    while j < n and not lines[j].strip():
                        j += 1
                    if j < n and len(lines[j]) - len(lines[j].lstrip()) > indent:
                        item.extend([""] * (j - i))
                        i = j
                        continue
                    following = pattern.match(lines[j]) if j < n else None
                    if following and len(following.group(1)) == indent:
                        i = j  # a loose list: the next item follows the blank line
                    break
                if len(nxt) - len(nxt.lstrip()) > indent:
                    item.append(nxt)
                    i += 1
                elif not self.starts_block(lines, i):
                    item.append(nxt.strip())  # lazy continuation
                    i += 1
                else:
                    break
            items.append(self.item(item, indent))
        tag = "ol" if ordered else "ul"
        return "<%s>%s</%s>" % (tag, "".join("<li>%s</li>" % x for x in items), tag), i

    def item(self, raw, indent):
        head, rest = raw[0], raw[1:]
        if not rest:
            return self.inline(head)
        width = min((len(l) - len(l.lstrip()) for l in rest if l.strip()), default=indent)
        body = [l[width:] if l.strip() else "" for l in rest]
        # Text lines directly under the first line continue its paragraph.
        lead = [head]
        while body and body[0].strip() and not self.starts_block(body, 0):
            lead.append(body.pop(0).strip())
        inner = self.blocks(body)
        return self.inline(" ".join(lead)) + "".join(inner)

    def table(self, lines, i):
        def cells(row):
            row = row.strip()
            if row.startswith("|"):
                row = row[1:]
            if row.endswith("|") and not row.endswith("\\|"):
                row = row[:-1]
            return [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", row)]

        header = cells(lines[i])
        aligns = []
        for c in cells(lines[i + 1]):
            left, right = c.startswith(":"), c.endswith(":")
            aligns.append("center" if left and right else "right" if right else "left" if left else None)
        rows = []
        j = i + 2
        while j < len(lines) and lines[j].strip():
            rows.append(cells(lines[j]))
            j += 1

        def tr(cols, tag):
            out = []
            for k, c in enumerate(cols):
                a = aligns[k] if k < len(aligns) and aligns[k] else None
                style = ' style="text-align:%s"' % a if a else ""
                out.append("<%s%s>%s</%s>" % (tag, style, self.inline(c), tag))
            return "<tr>%s</tr>" % "".join(out)

        return "<table><thead>%s</thead><tbody>%s</tbody></table>" % (
            tr(header, "th"), "".join(tr(r, "td") for r in rows))

    def render(self, markdown):
        text = COMMENT.sub("", markdown.replace("\r\n", "\n"))
        return "\n".join(self.blocks(text.split("\n")))


STYLE = """
:root {
  --bg: #fbfaf7; --fg: #1d1c1a; --muted: #6b6861; --line: #e6e2d8;
  --code-bg: #f0ede6; --accent: #b4540f; --tag: #ebe6da;
  color-scheme: light dark;
}
@media (prefers-color-scheme: dark) {
  :root { --bg: #141414; --fg: #e8e4dc; --muted: #9a958b; --line: #2b2a27;
          --code-bg: #1f1e1b; --accent: #f0a05a; --tag: #262522; }
}
* { box-sizing: border-box; }
html { -webkit-text-size-adjust: 100%; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font: 17px/1.6 ui-sans-serif, -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
}
main { max-width: 46rem; margin: 0 auto; padding: 3rem 16px 5rem; overflow-wrap: break-word; }
h1, h2, h3, h4 { line-height: 1.2; letter-spacing: -0.01em; }
h1 { font-size: 2.4rem; margin: 0 0 .5rem; }
h2 { font-size: 1.5rem; margin: 3rem 0 1rem; padding-top: 1rem; border-top: 1px solid var(--line); }
h3 { font-size: 1.15rem; margin: 2rem 0 .75rem; }
h2 a.anchor, h3 a.anchor { color: inherit; text-decoration: none; }
h2 a.anchor:hover::after, h3 a.anchor:hover::after { content: " #"; color: var(--muted); }
p, ul, ol, blockquote, pre, table { margin: 0 0 1.1rem; }
a { color: var(--accent); text-underline-offset: .15em; }
a:hover { text-decoration-thickness: 2px; }
blockquote { margin-left: 0; padding: .1rem 1rem; border-left: 3px solid var(--accent); color: var(--muted); font-size: 1.05em; }
blockquote p { margin: .5rem 0; }
ul, ol { padding-left: 1.4rem; }
li { margin: .35rem 0; }
li > ul, li > ol { margin: .35rem 0 0; }
code, pre { font: .88em/1.5 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
code { background: var(--code-bg); padding: .1em .35em; border-radius: 4px; }
pre { background: var(--code-bg); padding: .9rem 1rem; border-radius: 8px; overflow-x: auto; }
pre code { background: none; padding: 0; font-size: 1em; }
li > code { display: inline-block; max-width: 100%; font-size: .78em; background: var(--tag); color: var(--muted); vertical-align: baseline; }
li > a:first-child { font-weight: 600; }
table { width: 100%; border-collapse: collapse; font-size: .92em; display: block; overflow-x: auto; }
th, td { text-align: left; vertical-align: top; padding: .5rem .6rem; border-bottom: 1px solid var(--line); }
th { color: var(--muted); font-weight: 600; }
hr { border: 0; border-top: 1px solid var(--line); margin: 2rem 0; }
img { max-width: 100%; height: auto; }
a.shot { display: inline-block; width: calc(25% - .4rem); margin: .4rem .15rem .6rem 0; vertical-align: top; }
a.shot img { display: block; width: 100%; aspect-ratio: 16 / 10; object-fit: cover; border-radius: 6px; border: 1px solid var(--tag); }
dialog.viewer { border: 0; padding: 0; background: none; max-width: 96vw; max-height: 96vh; overflow: visible; }
dialog.viewer::backdrop { background: rgba(0, 0, 0, .82); }
dialog.viewer img { display: block; width: min(92vw, 1100px, 140.8vh); height: auto; border-radius: 8px; }
dialog.viewer p { margin: .6rem 0 0; text-align: center; color: #e8e4dc; font-size: .9rem; }
dialog.viewer button { position: fixed; top: 50%; transform: translateY(-50%); width: 2.75rem; height: 2.75rem; border: 0; border-radius: 50%; background: rgba(255, 255, 255, .16); color: #fff; font: inherit; font-size: 1.3rem; cursor: pointer; }
dialog.viewer button:hover { background: rgba(255, 255, 255, .3); }
dialog.viewer button[hidden] { display: none; }
dialog.viewer .prev { left: 12px; }
dialog.viewer .next { right: 12px; }
dialog.viewer .close { top: 12px; right: 12px; transform: none; }
em { color: var(--muted); }
.top { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; margin-bottom: 2rem; font-size: .9rem; color: var(--muted); }
.top a { color: inherit; }
footer { margin-top: 4rem; padding-top: 1rem; border-top: 1px solid var(--line); font-size: .85rem; color: var(--muted); }
"""

# Opens a screenshot in a dialog. Without scripting the link still opens the image.
SCRIPT = """
(function () {
  var viewer = document.querySelector("dialog.viewer");
  if (!viewer || !viewer.showModal) return;
  var image = viewer.querySelector("img"), caption = viewer.querySelector("p");
  var prev = viewer.querySelector(".prev"), next = viewer.querySelector(".next");
  var shots = [], at = 0;
  function show(i) {
    at = (i + shots.length) % shots.length;
    image.src = shots[at].href;
    image.alt = shots[at].firstElementChild.alt;
    caption.textContent = image.alt.replace(/ screenshot \\d+$/, "") + "  " + (at + 1) + " / " + shots.length;
    prev.hidden = next.hidden = shots.length < 2;
  }
  document.addEventListener("click", function (event) {
    var shot = event.target.closest && event.target.closest("a.shot");
    if (!shot || event.metaKey || event.ctrlKey || event.shiftKey || event.button) return;
    event.preventDefault();
    shots = Array.prototype.slice.call(shot.parentNode.querySelectorAll("a.shot"));
    show(shots.indexOf(shot));
    viewer.showModal();
  });
  prev.addEventListener("click", function () { show(at - 1); });
  next.addEventListener("click", function () { show(at + 1); });
  viewer.querySelector(".close").addEventListener("click", function () { viewer.close(); });
  viewer.addEventListener("click", function (event) { if (event.target === viewer) viewer.close(); });
  viewer.addEventListener("keydown", function (event) {
    if (event.key === "ArrowLeft") show(at - 1);
    if (event.key === "ArrowRight") show(at + 1);
  });
})();
"""

VIEWER = """<dialog class="viewer" aria-label="Screenshot">
<img src="data:," alt="">
<p></p>
<button class="prev" type="button" aria-label="Previous screenshot">&#8249;</button>
<button class="next" type="button" aria-label="Next screenshot">&#8250;</button>
<button class="close" type="button" aria-label="Close">&#215;</button>
</dialog>
<script>%s</script>
""" % SCRIPT.strip()

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{description}">
<link rel="icon" href="data:,">
<style>{style}</style>
</head>
<body>
<main>
{nav}
{body}
<footer>{footer}</footer>
</main>
{viewer}</body>
</html>
"""


def build(markdown, repo=None, branch="main"):
    """Returns (html, relative asset paths referenced by the page)."""
    r = Renderer(repo=repo, branch=branch)
    body = r.render(markdown)
    title = r.title or "README"
    description = ""
    m = re.search(r"<blockquote><p>(.*?)</p></blockquote>", body, re.S)
    if m:
        description = html.unescape(re.sub(r"<[^>]+>", "", m.group(1)))
    nav = ""
    footer = "Generated from README.md."
    if repo:
        url = "https://github.com/" + repo
        nav = '<div class="top"><span>%s</span><a href="%s">View on GitHub</a></div>' % (html.escape(repo), html.escape(url))
        footer = 'Generated from <a href="%s/blob/%s/README.md">README.md</a>.' % (html.escape(url), html.escape(branch))
    page = PAGE.format(
        title=html.escape(title), description=html.escape(description, quote=True),
        style=STYLE.strip(), nav=nav, body=body, footer=footer,
        viewer=VIEWER if 'class="shot"' in body else "",
    )
    return page, r.assets


def main():
    parser = argparse.ArgumentParser(description="Convert README.md to site/index.html for GitHub Pages.")
    parser.add_argument("--readme", default=str(ROOT / "README.md"), help="Markdown source (default: README.md)")
    parser.add_argument("--out", default=str(ROOT / "site"), help="Output directory (default: site/)")
    parser.add_argument("--repo", default=None, help="owner/name for resolving relative links (auto-detected)")
    parser.add_argument("--branch", default="main", help="branch used in resolved links (default: main)")
    args = parser.parse_args()

    markdown = Path(args.readme).read_text(encoding="utf-8")
    repo = repo_slug(args.repo)
    if not repo:
        print("warning: repository not detected; relative links are left as-is", file=sys.stderr)
    page, assets = build(markdown, repo=repo, branch=args.branch)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(page, encoding="utf-8")
    (out_dir / ".nojekyll").write_text("", encoding="utf-8")

    base = Path(args.readme).resolve().parent
    for rel in sorted(set(assets)):
        source = (base / rel).resolve()
        if base not in source.parents or not source.is_file():
            print("warning: %s: not found; left as a broken link" % rel, file=sys.stderr)
            continue
        target = out_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    print("wrote %s (%d assets)" % (out_dir / "index.html", len(set(assets))))


if __name__ == "__main__":
    main()
