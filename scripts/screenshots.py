#!/usr/bin/env python3
"""Captures up to four screenshots per list.json entry into assets/screenshots/.

Usage: python3 scripts/screenshots.py [--only owner/name ...] [--force]

Each entry has a directory assets/screenshots/<owner>__<name>/ holding
sources.json and the captures 1.webp to 4.webp. sources.json is a list of up
to four items, each a page or image URL, or {"url": ..., "y": pixels} to
capture a page scrolled down. An animated GIF is captured 60% of the way
through, or at {"url": ..., "t": fraction} from 0 to 1. A missing sources.json is detected once: the
repository homepage and the first README images. Edit it to pick better views,
then rerun with --only.

Needs Google Chrome or Chromium, and cwebp. GIF frames need ffmpeg and ffprobe;
without them a GIF shows its first frame. Only one browser runs at a time.
scripts/build.py adds the images that exist to an entry.
"""

import argparse
import fcntl
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "assets" / "screenshots"
MAX_SHOTS = 4
WIDTH, HEIGHT = 1280, 800  # browser viewport
OUT_WIDTH, OUT_HEIGHT = 640, 400  # stored size
MAX_Y = 6000
GIF_AT = 0.6  # default position in an animated GIF, as a fraction of its length
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"

CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]
CHROME_NAMES = ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]

IMG = re.compile(r'<img[^>]+src="([^"]+)"', re.I)
NOT_A_SCREENSHOT = re.compile(
    r"shields\.io|badge|/workflows/|travis-ci|codecov|opencollective|sponsor|buymeacoffee"
    r"|contrib\.rocks|star-history|vercel\.com/button|hits\.|logo|icon|avatar|banner",
    re.I,
)

WRAPPER = """<!doctype html><meta charset="utf-8">
<style>html,body{margin:0;height:100%%;background:#0d1117}
body{display:flex;align-items:center;justify-content:center}
img{max-width:100%%;max-height:100%%;object-fit:contain}</style>
<img src="%s">"""


def slug(repo):
    return repo.lower().replace("/", "__")


def entry_dir(repo):
    return SHOTS / slug(repo)


def shots(repo):
    """Existing captures of an entry, in order."""
    paths = [entry_dir(repo) / ("%d.webp" % n) for n in range(1, MAX_SHOTS + 1)]
    return [p for p in paths if p.exists()]


def find_chrome():
    env = os.environ.get("CHROME")
    for candidate in ([env] if env else []) + CHROME_PATHS:
        if Path(candidate).exists():
            return candidate
    for name in CHROME_NAMES:
        found = shutil.which(name)
        if found:
            return found
    sys.exit("Chrome not found. Set CHROME to the browser binary.")


def _token():
    env = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if env:
        return env
    try:
        return subprocess.run(
            ["gh", "auth", "token"], capture_output=True, text=True, check=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        sys.exit("No GitHub token. Set GITHUB_TOKEN or log in with the gh CLI.")


def gh(path, token, accept="application/vnd.github+json"):
    """GET a GitHub API path. Returns None on 404."""
    req = urllib.request.Request(
        "https://api.github.com" + path,
        headers={"Authorization": "Bearer " + token, "Accept": accept, "User-Agent": "awesome-beautiful-ui"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            body = res.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        if err.code == 404:
            return None
        raise SystemExit("%s: HTTP %s" % (path, err.code))
    return json.loads(body) if accept.endswith("+json") else body


def readme_images(repo, token):
    """README images that are not badges or logos, in order."""
    rendered = gh("/repos/%s/readme" % repo, token, accept="application/vnd.github.html") or ""
    found = []
    for src in IMG.findall(rendered):
        src = src.replace("&amp;", "&")
        if src.startswith("http") and not NOT_A_SCREENSHOT.search(src) and src not in found:
            found.append(src)
    return found


def detect_sources(entry, token):
    """Up to four URLs to capture for an entry. Empty when nothing usable was found."""
    data = gh("/repos/" + entry["repo"], token)
    if data is None:
        return []
    homepage = (data.get("homepage") or "").strip()
    if homepage and not homepage.startswith("http"):
        homepage = "https://" + homepage
    if "github.com/" + entry["repo"].lower() in homepage.lower():
        homepage = ""
    pages = [homepage] if homepage else []
    images = readme_images(entry["repo"], token)
    ordered = images + pages if entry["section"] == "terminal" else pages + images
    return ordered[:MAX_SHOTS]


def read_sources(repo):
    """The entry's sources as (url, y, t) tuples, or None when sources.json is missing."""
    path = entry_dir(repo) / "sources.json"
    if not path.exists():
        return None
    out = []
    for item in json.loads(path.read_text(encoding="utf-8"))[:MAX_SHOTS]:
        item_ = {"url": item} if isinstance(item, str) else item
        url, y, t = item_["url"], int(item_.get("y", 0)), float(item_.get("t", GIF_AT))
        if not url.startswith(("http://", "https://")) or not 0 <= y <= MAX_Y or not 0 <= t <= 1:
            sys.exit("%s: bad source %r" % (path, item))
        out.append((url, y, t))
    return out


def image_type(url):
    """The content type of url when it is an image, else an empty string."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            kind = res.headers.get_content_type()
            return kind if kind.startswith("image/") else ""
    except (urllib.error.URLError, OSError, ValueError):
        return ""


def gif_frame(url, t, png, tmp):
    """Write the frame at fraction t of an animated GIF to png, centered on the viewport."""
    gif = Path(tmp) / "source.gif"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            gif.write_bytes(res.read())
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(gif)],
            capture_output=True, text=True, timeout=120,
        )
        seconds = float(probe.stdout.strip() or 0) * t
        fit = ("scale='min(%d,iw)':'min(%d,ih)':force_original_aspect_ratio=decrease,"
               "pad=%d:%d:(ow-iw)/2:(oh-ih)/2:color=0x0d1117" % (WIDTH, HEIGHT, WIDTH, HEIGHT))
        # Seeking after -i decodes from the start, so the frame is fully composed.
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-i", str(gif), "-ss", "%.3f" % seconds, "-frames:v", "1", "-vf", fit, str(png)],
            capture_output=True, timeout=300,
        )
    except (urllib.error.URLError, OSError, ValueError, subprocess.TimeoutExpired):
        return False
    return png.exists() and png.stat().st_size > 0


def browser_shot(chrome, target, png, height, profile):
    """Run one headless browser until the screenshot file is complete, then stop it.

    The browser often keeps running after writing the file, so it is never
    waited on: its whole process group is killed once the file stops growing.
    """
    # One browser on the machine at a time, also across parallel runs of this script.
    with open(Path(tempfile.gettempdir()) / "awesome-beautiful-ui-browser.lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _browser_shot(chrome, target, png, height, profile)


def _browser_shot(chrome, target, png, height, profile):
    proc = subprocess.Popen(
        [
            chrome, "--headless=new", "--hide-scrollbars", "--no-first-run", "--mute-audio",
            "--user-data-dir=" + str(profile),
            "--window-size=%d,%d" % (WIDTH, height),
            "--virtual-time-budget=12000",
            "--user-agent=" + USER_AGENT,
            "--screenshot=" + str(png), target,
        ],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True,
    )
    try:
        deadline = time.time() + 60
        size = -1
        while time.time() < deadline:
            time.sleep(1)
            now = png.stat().st_size if png.exists() else -1
            if now > 0 and now == size:
                return True
            size = now
            if proc.poll() is not None and now <= 0:
                return False
        return False
    finally:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        proc.wait()


def capture(chrome, url, y, t, out):
    """Screenshot url, scrolled down by y pixels, into out. Returns an error string or None."""
    with tempfile.TemporaryDirectory() as tmp:
        target = url
        png = Path(tmp) / "shot.png"
        kind = image_type(url)
        if kind:
            wrapper = Path(tmp) / "image.html"
            wrapper.write_text(WRAPPER % url.replace('"', "%22"), encoding="utf-8")
            target, y = wrapper.as_uri(), 0
        framed = kind == "image/gif" and shutil.which("ffmpeg") and shutil.which("ffprobe") and gif_frame(url, t, png, tmp)
        # A scrolled view is a taller window cropped to its last screen.
        if not framed and not browser_shot(chrome, target, png, HEIGHT + y, Path(tmp) / "profile"):
            return "no screenshot produced"
        out.parent.mkdir(parents=True, exist_ok=True)
        done = subprocess.run(
            [
                "cwebp", "-quiet", "-q", "80", "-crop", "0", str(y), str(WIDTH), str(HEIGHT),
                "-resize", str(OUT_WIDTH), str(OUT_HEIGHT), str(png), "-o", str(out),
            ],
            capture_output=True, text=True,
        )
        return (done.stderr.strip() or "cwebp failed") if done.returncode else None


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", action="append", default=[], metavar="owner/name", help="capture just this entry; repeatable")
    parser.add_argument("--force", action="store_true", help="recapture entries that already have screenshots")
    args = parser.parse_args()

    if not shutil.which("cwebp"):
        sys.exit("cwebp not found. Install the webp tools.")
    chrome = find_chrome()
    entries = json.loads((ROOT / "list.json").read_text(encoding="utf-8"))
    only = {r.lower() for r in args.only}
    unknown = only - {e["repo"].lower() for e in entries}
    if unknown:
        sys.exit("not in list.json: %s" % ", ".join(sorted(unknown)))

    todo = [
        e for e in entries
        if (e["repo"].lower() in only if only else True)
        and (args.force or bool(only) or not shots(e["repo"]))
    ]
    missing = [e for e in todo if read_sources(e["repo"]) is None]
    if missing:
        token = _token()
        with ThreadPoolExecutor(max_workers=8) as pool:
            for e, urls in zip(missing, pool.map(lambda e: detect_sources(e, token), missing)):
                entry_dir(e["repo"]).mkdir(parents=True, exist_ok=True)
                (entry_dir(e["repo"]) / "sources.json").write_text(json.dumps(urls, indent=2) + "\n", encoding="utf-8")

    def run(job):
        repo, n, (url, y, t) = job
        return repo, n, url, capture(chrome, url, y, t, entry_dir(repo) / ("%d.webp" % n))

    jobs = []
    for e in todo:
        sources = read_sources(e["repo"])
        if not sources:
            print("FAIL\t%s\tno sources; add some to %s" % (e["repo"], (entry_dir(e["repo"]) / "sources.json").relative_to(ROOT)))
        for stale in shots(e["repo"])[len(sources):]:
            stale.unlink()
        jobs += [(e["repo"], n, source) for n, source in enumerate(sources, 1)]

    failed = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        for repo, n, url, error in pool.map(run, jobs):
            failed += bool(error)
            print("%s\t%s\t%d\t%s" % ("FAIL" if error else "ok", repo, n, error or url))
    print("%d captured, %d failed" % (len(jobs) - failed, failed))


if __name__ == "__main__":
    main()
