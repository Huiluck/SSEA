#!/usr/bin/env python3
"""
Sequential paper downloader - conservative rate to avoid arxiv 406.
Uses export.arxiv.org endpoint for arxiv papers.
Single-threaded with delays.
"""

import os
import re
import time
import urllib.request
import urllib.error

README_PATH = r"C:\MyDocs\AGI\README.md"
OUTPUT_DIR = r"C:\MyDocs\AGI\SSEA\docs\papers"
LOG_FILE = os.path.join(OUTPUT_DIR, "_sequential_log.txt")
TIMEOUT = 120
RETRIES = 3
ARXIV_DELAY = 4.0  # seconds between arxiv requests
OTHER_DELAY = 1.0

os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_paper_urls(text):
    urls = set()
    for m in re.finditer(r'\[\[Paper\]\]\(([^)]+)\)', text):
        urls.add(m.group(1).strip())
    for m in re.finditer(r'\[Paper\]\(([^)]+)\)', text):
        urls.add(m.group(1).strip())
    for m in re.finditer(r'https?://[^\s\)\]>"<>]+', text):
        url = m.group(0).rstrip('.,;')
        if any(domain in url for domain in [
            'arxiv.org', 'aclanthology.org', 'proceedings.neurips.cc',
            'openreview.net', 'nature.com', 'ojs.aaai.org',
            'neurips.cc', 'dl.acm.org'
        ]):
            if 'github.com' in url:
                continue
            if 'self-developing-agents.github.io' in url:
                continue
            urls.add(url)
    return sorted(urls)


def url_to_pdf_url(url):
    url = url.strip()
    if url.endswith('.pdf'):
        return url

    # arXiv - use export endpoint for bulk downloads
    m = re.match(r'https?://arxiv\.org/abs/([\w.\-]+)(v\d+)?', url)
    if m:
        return f"https://export.arxiv.org/pdf/{m.group(1)}.pdf"

    if re.match(r'https?://arxiv\.org/pdf/([\w.\-]+)\.pdf', url):
        arxiv_id = re.match(r'https?://arxiv\.org/pdf/([\w.\-]+)\.pdf', url).group(1)
        return f"https://export.arxiv.org/pdf/{arxiv_id}.pdf"

    # ACL anthology
    m = re.match(r'https?://aclanthology\.org/([\w.\-/]+?)/?$', url)
    if m:
        path = m.group(1).rstrip('/')
        if path.endswith('.pdf'):
            return f"https://aclanthology.org/{path}"
        return f"https://aclanthology.org/{path}.pdf"

    if 'aclanthology.org/anthology-files' in url and url.endswith('.pdf'):
        return url

    m = re.match(r'https?://aclanthology\.org/anthology-files/pdf/[\w/]+/([\w.\-]+)\.pdf', url)
    if m:
        return f"https://aclanthology.org/{m.group(1)}.pdf"

    # NeurIPS
    m = re.match(
        r'https?://proceedings\.neurips\.cc/paper_files/paper/(\d{4})/hash/([\w]+)-Abstract-(Conference|Datasets_and_Benchmarks)\.html',
        url)
    if m:
        year, h, typ = m.group(1), m.group(2), m.group(3)
        return f"https://proceedings.neurips.cc/paper_files/paper/{year}/file/{h}-Paper-{typ}.pdf"

    m = re.match(
        r'https?://proceedings\.neurips\.cc/paper/(\d{4})/hash/([\w]+)-Abstract\.html',
        url)
    if m:
        year, h = m.group(1), m.group(2)
        return f"https://proceedings.neurips.cc/paper/{year}/file/{h}-Paper.pdf"

    # OpenReview
    m = re.match(r'https?://openreview\.net/forum\?id=([\w\-]+)', url)
    if m:
        return f"https://openreview.net/pdf?id={m.group(1)}"

    # Nature
    if 'nature.com/articles/' in url and not url.endswith('.pdf'):
        return url + ".pdf"

    # Virtual posters - skip
    if 'icml.cc/virtual' in url or 'neurips.cc/virtual' in url:
        return None

    # AAAI
    if 'ojs.aaai.org' in url and '/article/view/' in url:
        return url + '/pdf'

    return None


def safe_filename(original_url):
    m = re.search(r'arxiv\.org/(?:abs|pdf)/([\w.\-]+)', original_url)
    if m:
        return f"arxiv_{m.group(1)}.pdf"
    m = re.search(r'aclanthology\.org/([\w.\-]+)', original_url)
    if m:
        aid = m.group(1)
        if aid.endswith('.pdf'):
            aid = aid[:-4]
        return f"acl_{aid}.pdf"
    m = re.search(r'neurips\.cc.*?/hash/([\w]+)', original_url)
    if m:
        return f"neurips_{m.group(1)[:16]}.pdf"
    m = re.search(r'openreview\.net/(?:forum|pdf)\?id=([\w\-]+)', original_url)
    if m:
        return f"openreview_{m.group(1)}.pdf"
    m = re.search(r'nature\.com/articles/([\w.\-]+)', original_url)
    if m:
        return f"nature_{m.group(1)}.pdf"
    import hashlib
    h = hashlib.md5(original_url.encode()).hexdigest()[:12]
    return f"paper_{h}.pdf"


def download_one(pdf_url, original_url, output_path):
    if pdf_url is None:
        return False, "No PDF URL"

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
        return True, "Already exists"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(pdf_url, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = resp.read()

            if len(data) < 1024:
                return False, f"Too small ({len(data)} bytes)"

            if not data.startswith(b'%PDF'):
                return False, f"Not PDF (size: {len(data)})"

            with open(output_path, 'wb') as f:
                f.write(data)
            return True, f"OK ({len(data)//1024} KB)"

        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False, "HTTP 404"
            if e.code == 406 or e.code == 429:
                if attempt < RETRIES - 1:
                    wait = 10 * (attempt + 1)
                    print(f"    Rate limited (HTTP {e.code}), waiting {wait}s...")
                    time.sleep(wait)
                    continue
                return False, f"HTTP {e.code} (rate limited)"
            if attempt == RETRIES - 1:
                return False, f"HTTP {e.code}"
            time.sleep(5)
        except Exception as e:
            if attempt == RETRIES - 1:
                return False, f"Error: {str(e)[:80]}"
            time.sleep(5)

    return False, "Max retries"


def main():
    existing = set(f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf'))
    print(f"Already downloaded: {len(existing)} files")

    with open(README_PATH, 'r', encoding='utf-8') as f:
        text = f.read()

    urls = extract_paper_urls(text)
    print(f"Total paper URLs: {len(urls)}")

    # Build task list
    tasks = []
    for original_url in urls:
        fname = safe_filename(original_url)
        if fname in existing:
            continue
        pdf_url = url_to_pdf_url(original_url)
        if pdf_url is None:
            continue
        output_path = os.path.join(OUTPUT_DIR, fname)
        is_arxiv = 'arxiv.org' in pdf_url
        tasks.append((pdf_url, original_url, output_path, is_arxiv))

    print(f"Need to download: {len(tasks)} papers")
    arxiv_count = sum(1 for t in tasks if t[3])
    print(f"  (arXiv: {arxiv_count}, other: {len(tasks) - arxiv_count})")

    if not tasks:
        print("Nothing to do!")
        return

    results = []
    success_count = 0

    for i, (pdf_url, original_url, output_path, is_arxiv) in enumerate(tasks, 1):
        delay = ARXIV_DELAY if is_arxiv else OTHER_DELAY

        print(f"[{i}/{len(tasks)}] {original_url[:80]}")
        success, msg = download_one(pdf_url, original_url, output_path)
        results.append((success, msg, original_url, pdf_url))

        if success:
            success_count += 1
            print(f"    -> {msg}")
        else:
            print(f"    -> FAIL: {msg}")

        # Delay before next (skip after last)
        if i < len(tasks):
            time.sleep(delay)

        # Progress report every 20
        if i % 20 == 0:
            print(f"\n  --- Progress: {i}/{len(tasks)}, Success: {success_count} ---\n")

    fail_count = len(results) - success_count
    final_files = set(f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf'))

    print(f"\n{'='*60}")
    print(f"FINAL: Attempted={len(results)}, Success={success_count}, Failed={fail_count}")
    print(f"Total PDF files in folder: {len(final_files)}")
    print(f"{'='*60}")

    # Write log
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"Sequential Download Log - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Attempted: {len(results)}, Success: {success_count}, Failed: {fail_count}\n")
        f.write(f"Total PDFs: {len(final_files)}\n")
        f.write("=" * 60 + "\n\n")
        f.write("--- FAILED ---\n")
        for success, msg, original, used in results:
            if not success:
                f.write(f"[FAIL] {original}\n       {msg}\n       PDF URL: {used}\n\n")


if __name__ == '__main__':
    main()
