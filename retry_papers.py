#!/usr/bin/env python3
"""Retry failed paper downloads with fixes."""

import os
import re
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

README_PATH = r"C:\MyDocs\AGI\README.md"
OUTPUT_DIR = r"C:\MyDocs\AGI\SSEA\docs\papers"
LOG_FILE = os.path.join(OUTPUT_DIR, "_retry_log.txt")
MAX_WORKERS = 3
TIMEOUT = 90
RETRIES = 4

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
            'openreview.net', 'nature.com', 'icml.cc', 'ojs.aaai.org',
            'neurips.cc', 'dl.acm.org'
        ]):
            if 'github.com' in url:
                continue
            if 'self-developing-agents.github.io' in url:
                continue
            urls.add(url)
    return sorted(urls)


def url_to_pdf_url(url):
    """Convert paper page URL to direct PDF URL - FIXED version."""
    url = url.strip()

    # Already a PDF
    if url.endswith('.pdf'):
        return url

    # arXiv abs -> pdf
    m = re.match(r'https?://arxiv\.org/abs/([\w.\-]+)(v\d+)?', url)
    if m:
        return f"https://arxiv.org/pdf/{m.group(1)}.pdf"

    # arXiv pdf already
    if re.match(r'https?://arxiv\.org/pdf/[\w.\-]+\.pdf', url):
        return url

    # ACL anthology page (NOT ending in .pdf) -> append .pdf
    m = re.match(r'https?://aclanthology\.org/([\w.\-/]+?)/?$', url)
    if m:
        path = m.group(1).rstrip('/')
        # Don't double-append .pdf
        if path.endswith('.pdf'):
            return f"https://aclanthology.org/{path}"
        return f"https://aclanthology.org/{path}.pdf"

    # ACL anthology-files direct PDF (already ends with .pdf)
    if 'aclanthology.org/anthology-files' in url and url.endswith('.pdf'):
        return url

    # ACL anthology-files page -> convert to canonical
    m = re.match(r'https?://aclanthology\.org/anthology-files/pdf/[\w/]+/([\w.\-]+)\.pdf', url)
    if m:
        # Try canonical URL instead
        return f"https://aclanthology.org/{m.group(1)}.pdf"

    # NeurIPS proceedings
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

    # ICML / NeurIPS virtual posters - skip (no direct PDF)
    if 'icml.cc/virtual' in url or 'neurips.cc/virtual' in url:
        return None

    # AAAI
    if 'ojs.aaai.org' in url and '/article/view/' in url:
        return url + '/pdf'

    if url.endswith('.pdf'):
        return url

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
        return False, "No PDF URL", original_url

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
        return True, "Already exists", original_url

    # Use browser-like headers, no restrictive Accept
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    }

    for attempt in range(RETRIES):
        try:
            # Small delay for arxiv to avoid rate limit
            if 'arxiv.org' in pdf_url:
                time.sleep(1.0)

            req = urllib.request.Request(pdf_url, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                data = resp.read()

            if len(data) < 1024:
                return False, f"Too small ({len(data)} bytes)", pdf_url

            if not data.startswith(b'%PDF'):
                return False, f"Not PDF (size: {len(data)}, starts: {data[:20]})", pdf_url

            with open(output_path, 'wb') as f:
                f.write(data)
            return True, f"Downloaded ({len(data)} bytes)", pdf_url

        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False, "HTTP 404", pdf_url
            if e.code == 406:
                # arxiv rate limit - wait longer
                if attempt < RETRIES - 1:
                    time.sleep(5 * (attempt + 1))
                    continue
                return False, "HTTP 406 (rate limited)", pdf_url
            if attempt == RETRIES - 1:
                return False, f"HTTP {e.code}", pdf_url
            time.sleep(3 * (attempt + 1))
        except Exception as e:
            if attempt == RETRIES - 1:
                return False, f"Error: {str(e)[:100]}", pdf_url
            time.sleep(3 * (attempt + 1))

    return False, "Max retries", pdf_url


def main():
    # Get existing files
    existing = set(f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf'))
    print(f"Already downloaded: {len(existing)} files")

    # Read and parse README
    with open(README_PATH, 'r', encoding='utf-8') as f:
        text = f.read()

    urls = extract_paper_urls(text)
    print(f"Total paper URLs in README: {len(urls)}")

    # Build tasks, skip already downloaded
    tasks = []
    for original_url in urls:
        fname = safe_filename(original_url)
        if fname in existing:
            continue
        pdf_url = url_to_pdf_url(original_url)
        if pdf_url is None:
            continue
        output_path = os.path.join(OUTPUT_DIR, fname)
        tasks.append((pdf_url, original_url, output_path))

    print(f"Need to download: {len(tasks)} papers")

    if not tasks:
        print("Nothing to do!")
        return

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for pdf_url, original_url, output_path in tasks:
            future = executor.submit(download_one, pdf_url, original_url, output_path)
            futures[future] = original_url

        for i, future in enumerate(as_completed(futures), 1):
            success, msg, used_url = future.result()
            original = futures[future]
            results.append((success, msg, original, used_url))
            if i % 20 == 0 or i == len(tasks):
                print(f"  Progress: {i}/{len(tasks)} (success so far: {sum(1 for r in results if r[0])})")

    success_count = sum(1 for r in results if r[0])
    fail_count = len(results) - success_count
    print(f"\n=== Retry Summary ===")
    print(f"Attempted: {len(results)}, Success: {success_count}, Failed: {fail_count}")

    # Final count
    final_files = set(f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf'))
    print(f"Total PDF files now: {len(final_files)}")

    # Write retry log
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"Retry Log - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Attempted: {len(results)}, Success: {success_count}, Failed: {fail_count}\n")
        f.write(f"Total PDFs in folder: {len(final_files)}\n")
        f.write("=" * 80 + "\n\n")
        f.write("--- STILL FAILED ---\n")
        for success, msg, original, used in results:
            if not success:
                f.write(f"[FAIL] {original}\n       Reason: {msg}\n       Tried: {used}\n\n")


if __name__ == '__main__':
    main()
