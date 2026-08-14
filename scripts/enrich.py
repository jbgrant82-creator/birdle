#!/usr/bin/env python3
"""Enrichment pipeline for the Birdle word bank.

For every word in data/wordbank.json, fetches a Wikipedia summary, downloads
and licenses a photo (bird_species / bird_adjacent only — never for
character entries, see HANDOFF.md §4), and optionally pulls a Xeno-canto
audio clip for bird_species entries (requires an XC_API_KEY env var — see
HANDOFF.md §6). Writes data/entries/{WORD}.json and data/review-queue.json.

Usage:
    python3 scripts/enrich.py                 # full run, resumable
    python3 scripts/enrich.py --limit 10       # smoke test
    python3 scripts/enrich.py --only ROBIN,ZAZU
    python3 scripts/enrich.py --force          # re-fetch everything
    python3 scripts/enrich.py --no-audio       # skip Xeno-canto even if keyed
"""
import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path

import requests
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
ENTRIES_DIR = DATA / "entries"
ASSETS = ROOT / "assets"
BIRDS_DIR = ASSETS / "birds"
AUDIO_DIR = ASSETS / "audio"
CACHE_DIR = ROOT / ".cache"
REVIEW_QUEUE_PATH = DATA / "review-queue.json"
WORDBANK_PATH = DATA / "wordbank.json"

USER_AGENT = (
    "Birdle-Enrichment/0.1 (personal word-game project; "
    "contact: jbgrant82@gmail.com)"
)
REQUEST_DELAY = 1.05  # seconds between *live* network hits (cache hits are free)
XC_API_KEY = os.environ.get("XC_API_KEY")

for d in (ENTRIES_DIR, BIRDS_DIR, AUDIO_DIR, CACHE_DIR):
    d.mkdir(parents=True, exist_ok=True)

session = requests.Session()
session.headers.update({"User-Agent": USER_AGENT})

_last_request_time = [0.0]


def _throttle():
    elapsed = time.monotonic() - _last_request_time[0]
    if elapsed < REQUEST_DELAY:
        time.sleep(REQUEST_DELAY - elapsed)
    _last_request_time[0] = time.monotonic()


def _cache_path(url, ext):
    key = hashlib.sha1(url.encode()).hexdigest()
    return CACHE_DIR / f"{key}.{ext}"


def get_json(url, params=None, tries=2):
    full_url = url + ("?" + urllib.parse.urlencode(params) if params else "")
    cache_file = _cache_path(full_url, "json")
    if cache_file.exists():
        return json.loads(cache_file.read_text())
    for attempt in range(tries):
        try:
            _throttle()
            resp = session.get(full_url, timeout=15)
            if resp.status_code == 404:
                cache_file.write_text(json.dumps({"__404__": True}))
                return {"__404__": True}
            resp.raise_for_status()
            data = resp.json()
            cache_file.write_text(json.dumps(data))
            return data
        except (requests.RequestException, ValueError) as e:
            if attempt == tries - 1:
                print(f"    ! request failed for {full_url}: {e}", file=sys.stderr)
                return None
            time.sleep(1.5)
    return None


def get_bytes(url, tries=2):
    cache_file = _cache_path(url, "bin")
    if cache_file.exists():
        return cache_file.read_bytes()
    for attempt in range(tries):
        try:
            _throttle()
            resp = session.get(url, timeout=30)
            resp.raise_for_status()
            cache_file.write_bytes(resp.content)
            return resp.content
        except requests.RequestException as e:
            if attempt == tries - 1:
                print(f"    ! download failed for {url}: {e}", file=sys.stderr)
                return None
            time.sleep(1.5)
    return None


# --------------------------------------------------------------- wikipedia

WIKI_SUMMARY = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
WIKI_SEARCH = "https://en.wikipedia.org/w/api.php"


def wiki_search_fallback(query):
    data = get_json(
        WIKI_SEARCH,
        params={
            "action": "query",
            "list": "search",
            "srsearch": query,
            "format": "json",
            "srlimit": 1,
        },
    )
    if not data:
        return None
    hits = data.get("query", {}).get("search", [])
    return hits[0]["title"] if hits else None


def fetch_wiki_summary(word, hint, category, issues):
    title = hint
    data = get_json(WIKI_SUMMARY.format(urllib.parse.quote(title, safe="")))

    if data is None or data.get("__404__"):
        fallback_query = f"{word} bird" if category != "character" else word
        fb_title = wiki_search_fallback(fallback_query)
        if not fb_title:
            issues.append({"word": word, "issue": "not-found",
                            "detail": f"no wikipedia page for hint '{hint}'"})
            return None
        title = fb_title
        data = get_json(WIKI_SUMMARY.format(urllib.parse.quote(title, safe="")))
        if data is None or data.get("__404__"):
            issues.append({"word": word, "issue": "not-found",
                            "detail": f"search fallback '{fb_title}' also 404'd"})
            return None

    if data.get("type") == "disambiguation":
        fallback_query = f"{word} bird" if category != "character" else word
        fb_title = wiki_search_fallback(fallback_query)
        if fb_title and fb_title != title:
            retry = get_json(WIKI_SUMMARY.format(urllib.parse.quote(fb_title, safe="")))
            if retry and not retry.get("__404__") and retry.get("type") != "disambiguation":
                data = retry
                title = fb_title
        if data.get("type") == "disambiguation":
            issues.append({"word": word, "issue": "disambiguation",
                            "detail": f"'{title}' is a disambiguation page"})
            return data  # still return so caller can salvage a link

    resolved_title = data.get("title", title)
    # Only worth a human's attention when the fetch DIDN'T land on the hint
    # as written (redirect, disambiguation fallback, 404 fallback) — if the
    # hint's own title came back verbatim, that was already the human's call.
    if resolved_title != hint and not title_plausible(word, resolved_title):
        issues.append({"word": word, "issue": "title-mismatch",
                        "detail": f"hint '{hint}' -> resolved title "
                                  f"'{resolved_title}', doesn't obviously match"})

    return data


def title_plausible(word, title):
    w = word.lower()
    t = re.sub(r"\s*\(.*?\)\s*$", "", title).lower().strip()
    if w in t or t in w:
        return True
    wt = set(re.findall(r"[a-z]+", w))
    tt = set(re.findall(r"[a-z]+", t))
    return bool(wt & tt)


def split_sentences(text):
    if not text:
        return []
    return re.split(r"(?<=[.!?])\s+(?=[A-Z0-9])", text.strip())


def make_blurb(extract, limit=250):
    sentences = split_sentences(extract)
    if not sentences:
        return ""
    blurb = sentences[0]
    if len(blurb) < limit and len(sentences) > 1:
        candidate = blurb + " " + sentences[1]
        if len(candidate) <= limit:
            blurb = candidate
    if len(blurb) > limit:
        blurb = blurb[:limit].rsplit(" ", 1)[0] + "..."
    return blurb, len(split_sentences(extract)[:2])


def make_facts(extract, skip_sentences):
    sentences = split_sentences(extract)[skip_sentences:]
    facts = []
    for s in sentences:
        s = s.strip()
        if not s or len(s) < 15:
            continue
        if len(s) > 180:
            s = s[:180].rsplit(" ", 1)[0] + "..."
        facts.append(s)
        if len(facts) == 3:
            break
    return facts


# ----------------------------------------------------------------- images

COMMONS_API = "https://commons.wikimedia.org/w/api.php"


def commons_filename_from_url(url):
    path = urllib.parse.urlparse(url).path
    parts = path.split("/")
    if "thumb" in parts:
        idx = parts.index("thumb")
        try:
            return urllib.parse.unquote(parts[idx + 3])
        except IndexError:
            return None
    return urllib.parse.unquote(parts[-1]) if parts else None


def fetch_license(image_url, word, issues):
    if "/wikipedia/commons/" not in image_url:
        issues.append({"word": word, "issue": "unclear-license",
                        "detail": f"image hosted outside Commons ({image_url}), "
                                  "likely a non-free local file — not downloaded"})
        return None
    filename = commons_filename_from_url(image_url)
    if not filename:
        issues.append({"word": word, "issue": "unclear-license",
                        "detail": f"couldn't parse Commons filename from {image_url}"})
        return None
    data = get_json(COMMONS_API, params={
        "action": "query", "titles": f"File:{filename}",
        "prop": "imageinfo", "iiprop": "extmetadata", "format": "json",
    })
    if not data:
        issues.append({"word": word, "issue": "unclear-license",
                        "detail": f"Commons imageinfo lookup failed for {filename}"})
        return None
    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
    meta = page.get("imageinfo", [{}])[0].get("extmetadata", {})
    license_short = meta.get("LicenseShortName", {}).get("value")
    artist_html = meta.get("Artist", {}).get("value", "")
    artist = re.sub(r"<[^>]+>", "", artist_html).strip() or "unknown"
    license_url = meta.get("LicenseUrl", {}).get("value", "")

    if not license_short or re.search(r"non-free|fair use|all rights reserved",
                                       license_short, re.I):
        issues.append({"word": word, "issue": "unclear-license",
                        "detail": f"license '{license_short}' on {filename} "
                                  "is missing or looks non-free — not downloaded"})
        return None

    return {
        "license_short": license_short,
        "artist": artist,
        "license_url": license_url,
        "commons_file": filename,
        "commons_page": f"https://commons.wikimedia.org/wiki/File:{filename}",
    }


def process_and_save_image(raw_bytes, word):
    try:
        img = Image.open(io.BytesIO(raw_bytes))
        img = img.convert("RGB")
        if img.width > 800:
            h = round(img.height * 800 / img.width)
            img = img.resize((800, h), Image.LANCZOS)
        webp_path = BIRDS_DIR / f"{word}.webp"
        jpg_path = BIRDS_DIR / f"{word}.jpg"
        img.save(webp_path, "WEBP", quality=82, method=6)
        img.save(jpg_path, "JPEG", quality=85, progressive=True)
        return webp_path, jpg_path
    except Exception as e:
        print(f"    ! image processing failed for {word}: {e}", file=sys.stderr)
        return None, None


def fetch_image(summary, word, issues):
    image_url = (summary.get("originalimage") or {}).get("source") or \
                (summary.get("thumbnail") or {}).get("source")
    if not image_url:
        issues.append({"word": word, "issue": "missing-image",
                        "detail": "no thumbnail/originalimage on wikipedia summary"})
        return None

    license_info = fetch_license(image_url, word, issues)
    if not license_info:
        return None

    raw = get_bytes(image_url)
    if not raw:
        issues.append({"word": word, "issue": "missing-image",
                        "detail": f"download failed for {image_url}"})
        return None

    webp_path, jpg_path = process_and_save_image(raw, word)
    if not webp_path:
        issues.append({"word": word, "issue": "missing-image",
                        "detail": "downloaded but failed to process/resize"})
        return None

    return {
        "file": str(webp_path.relative_to(ROOT)),
        "file_jpg": str(jpg_path.relative_to(ROOT)),
        "alt": f"Photo of {summary.get('title', word.title())}",
        "credit": f"Photo by {license_info['artist']} — "
                  f"{license_info['license_short']}, via Wikimedia Commons",
        "credit_url": license_info["commons_page"],
    }


# ------------------------------------------------------------------ audio

XC_API = "https://xeno-canto.org/api/3/recordings"
TYPE_PRIORITY = {"song": 0, "call": 1}


def xc_search(common_name):
    if not XC_API_KEY:
        return None
    data = get_json(XC_API, params={"query": f'en:"{common_name}"', "key": XC_API_KEY})
    recs = (data or {}).get("recordings", [])
    if not recs:
        data = get_json(XC_API, params={"query": common_name, "key": XC_API_KEY})
        recs = (data or {}).get("recordings", [])
    return recs


def pick_recording(recs):
    def sort_key(r):
        rtype = (r.get("type") or "").lower()
        type_rank = min((rank for kw, rank in TYPE_PRIORITY.items() if kw in rtype), default=2)
        quality = r.get("q") or "E"
        quality_rank = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4}.get(quality, 5)
        return (type_rank, quality_rank)
    usable = [r for r in recs if r.get("file")]
    if not usable:
        return None
    usable.sort(key=sort_key)
    return usable[0]


def license_from_xc(lic_url):
    m = re.search(r"licenses/([\w-]+)/([\d.]+)", lic_url or "")
    if not m:
        return "Unknown license"
    return f"CC {m.group(1).upper()} {m.group(2)}"


def fetch_audio(word, summary_title, category, issues, audio_stats):
    if category != "bird_species":
        return None
    audio_stats["eligible"] += 1
    if not XC_API_KEY:
        audio_stats["skipped_no_key"] += 1
        return None

    recs = xc_search(summary_title)
    if not recs:
        audio_stats["no_recording"] += 1
        return None
    rec = pick_recording(recs)
    if not rec:
        audio_stats["no_recording"] += 1
        return None

    file_url = rec["file"]
    if file_url.startswith("//"):
        file_url = "https:" + file_url
    raw = get_bytes(file_url)
    if not raw:
        audio_stats["download_failed"] += 1
        return None

    raw_path = CACHE_DIR / f"xc_{word}_raw"
    raw_path.write_bytes(raw)

    webm_path = AUDIO_DIR / f"{word}.webm"
    mp3_path = AUDIO_DIR / f"{word}.mp3"
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(raw_path)],
            capture_output=True, text=True, timeout=30,
        )
        duration = float(probe.stdout.strip() or 0)
        start = min(1.0, duration * 0.1) if duration else 0
        end = min(start + 5, duration) if duration else 6
        af = f"atrim=start={start}:end={end},loudnorm=I=-16:TP=-1.5:LRA=11"
        for out_path, codec_args in (
            (webm_path, ["-c:a", "libopus", "-b:a", "64k"]),
            (mp3_path, ["-c:a", "libmp3lame", "-b:a", "96k"]),
        ):
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(raw_path), "-af", af, "-ac", "1",
                 *codec_args, str(out_path)],
                capture_output=True, timeout=60, check=True,
            )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as e:
        audio_stats["encode_failed"] += 1
        print(f"    ! audio encode failed for {word}: {e}", file=sys.stderr)
        return None
    finally:
        raw_path.unlink(missing_ok=True)

    audio_stats["success"] += 1
    rec_type = rec.get("type", "call")
    return {
        "file": str(webm_path.relative_to(ROOT)),
        "fallback": str(mp3_path.relative_to(ROOT)),
        "label": f"{rec_type.capitalize()} of the {summary_title.lower()}, "
                 f"recorded in {rec.get('cnt', 'unknown location')}",
        "duration_sec": round(end - start, 1),
        "credit": f"Recording by {rec.get('rec', 'unknown')} — "
                  f"{license_from_xc(rec.get('lic'))}, via Xeno-canto",
        "credit_url": rec.get("url", "https://xeno-canto.org"),
    }


# ------------------------------------------------------------------- main

CHARACTER_FIELDS = ["appearances", "creators", "studio", "first_appearance"]


def build_entry(word_entry, audio_stats):
    word = word_entry["word"]
    category = word_entry["category"]
    hint = word_entry["wikipedia_hint"]
    issues = []  # scoped to this word only; persisted on the entry and

    summary = fetch_wiki_summary(word, hint, category, issues)
    if summary is None:
        entry = {
            "word": word, "category": category, "title": None,
            "blurb": None, "facts": [], "link": None, "image": None,
            "verified": False,
        }
        if category == "character":
            entry.update({f: None for f in CHARACTER_FIELDS})
            entry["needs_hand_fill"] = True
        if category == "bird_species":
            entry["audio"] = None
        entry["_review_issues"] = issues
        return entry

    title = summary.get("title", hint)
    extract = summary.get("extract", "")
    blurb, skip_n = make_blurb(extract) if extract else ("", 0)
    facts = make_facts(extract, skip_n) if extract else []
    link = {
        "label": "Wikipedia",
        "url": summary.get("content_urls", {}).get("desktop", {}).get("page")
        or f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title)}",
    }

    entry = {
        "word": word,
        "category": category,
        "title": title,
        "blurb": blurb,
        "facts": facts,
        "link": link,
        "verified": False,
    }

    if category == "character":
        entry["image"] = None
        entry["image_note"] = (
            "trademarked — no image, see HANDOFF.md §4" if word_entry.get("trademarked")
            else "not flagged trademarked, but image was NOT auto-fetched — "
                 "verify individually before adding one, see HANDOFF.md §4"
        )
        entry.update({f: None for f in CHARACTER_FIELDS})
        entry["needs_hand_fill"] = True
        entry["audio"] = None
        entry["audio_note"] = "character entries never get audio, see HANDOFF.md §6"
    else:
        entry["image"] = fetch_image(summary, word, issues)
        if category == "bird_adjacent":
            entry["audio"] = None
            entry["audio_note"] = ("bird_adjacent words get no audio — there's no "
                                    "sound of a GIZZARD, see HANDOFF.md §6")
        else:
            entry["audio"] = fetch_audio(word, title, category, issues, audio_stats)

    entry["_review_issues"] = issues
    return entry


def rebuild_review_queue():
    """Re-derive review-queue.json from every entry currently on disk, so a
    partial/--only run never clobbers issues recorded for untouched words."""
    all_issues = []
    for f in sorted(ENTRIES_DIR.glob("*.json")):
        entry = json.loads(f.read_text())
        for issue in entry.get("_review_issues", []):
            all_issues.append(issue)
    REVIEW_QUEUE_PATH.write_text(json.dumps({
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "count": len(all_issues),
        "by_issue": {k: sum(1 for i in all_issues if i["issue"] == k)
                     for k in sorted({i["issue"] for i in all_issues})},
        "issues": all_issues,
    }, indent=2))
    return all_issues


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--only", type=str, default=None,
                     help="comma-separated words, e.g. ROBIN,ZAZU")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--no-audio", action="store_true")
    args = ap.parse_args()

    global XC_API_KEY
    if args.no_audio:
        XC_API_KEY = None

    bank = json.loads(WORDBANK_PATH.read_text())
    words = bank["words"]

    if args.only:
        wanted = {w.strip().upper() for w in args.only.split(",")}
        words = [w for w in words if w["word"] in wanted]
    if args.limit:
        words = words[: args.limit]

    audio_stats = {"eligible": 0, "skipped_no_key": 0, "no_recording": 0,
                    "download_failed": 0, "encode_failed": 0, "success": 0}
    processed = 0
    image_success = 0
    image_attempted = 0

    if not XC_API_KEY and not args.no_audio:
        print("NOTE: XC_API_KEY not set — Xeno-canto requires a registered key "
              "as of Oct 2025. Audio will be skipped for all species this run. "
              "Get a key at your xeno-canto.org account page, "
              "`export XC_API_KEY=...`, then re-run with --only "
              "or on bird_species entries to backfill audio.\n")

    for w in words:
        word = w["word"]
        entry_path = ENTRIES_DIR / f"{word}.json"
        if entry_path.exists() and not args.force:
            existing = json.loads(entry_path.read_text())
            if existing.get("verified") or existing.get("title"):
                continue

        print(f"[{processed + 1}/{len(words)}] {word} ({w['category']}, "
              f"hint='{w['wikipedia_hint']}')")
        entry = build_entry(w, audio_stats)
        entry_path.write_text(json.dumps(entry, indent=2))
        processed += 1

        if w["category"] != "character":
            image_attempted += 1
            if entry.get("image"):
                image_success += 1

    issues = rebuild_review_queue()

    print("\n" + "=" * 60)
    print(f"processed: {processed} words")
    print(f"images: {image_success}/{image_attempted} succeeded "
          f"({image_attempted - image_success} missing/unlicensed)")
    print(f"audio (bird_species only, {audio_stats['eligible']} eligible):")
    for k in ("success", "skipped_no_key", "no_recording", "download_failed", "encode_failed"):
        print(f"  {k}: {audio_stats[k]}")
    print(f"review queue: {len(issues)} issues -> {REVIEW_QUEUE_PATH.relative_to(ROOT)}")
    by_issue = {}
    for i in issues:
        by_issue[i["issue"]] = by_issue.get(i["issue"], 0) + 1
    for k, v in sorted(by_issue.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
