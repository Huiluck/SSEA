#!/usr/bin/env python3
"""Download all papers referenced in README.md into docs/papers/."""

import os
import re
import time
import hashlib
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

README_PATH = r"C:\MyDocs\AGI\README.md"
OUTPUT_DIR = r"C:\MyDocs\AGI\SSEA\docs\papers"
LOG_FILE = os.path.join(OUTPUT_DIR, "_download_log.txt")
MAX_WORKERS = 8
TIMEOUT = 60
RETRIES = 3

os.makedirs(OUTPUT_DIR, exist_ok=True)


def extract_paper_urls(text):
    """Extract all paper URLs from markdown."""
    urls = set()

    # Pattern 1: [[Paper]](url)
    for m in re.finditer(r'\[\[Paper\]\]\(([^)]+)\)', text):
        urls.add(m.group(1).strip())

    # Pattern 2: [Paper](url) - standalone
    for m in re.finditer(r'\[Paper\]\(([^)]+)\)', text):
        urls.add(m.group(1).strip())

    # Pattern 3: table rows with | [[Paper]](url) | - already covered
    # Pattern 4: direct arxiv/acl/neurips links in text
    for m in re.finditer(r'https?://[^\s\)\]>"<>]+', text):
        url = m.group(0).rstrip('.,;')
        # Only include likely paper URLs
        if any(domain in url for domain in [
            'arxiv.org', 'aclanthology.org', 'proceedings.neurips.cc',
            'openreview.net', 'nature.com', 'icml.cc', 'ojs.aaai.org',
            'neurips.cc', 'dl.acm.org', 'huggingface.co/datasets',
            'techrxiv.org', 'ssrn.com', 'analemma.ai'
        ]):
            # Skip github links (code repos, not papers)
            if 'github.com' in url:
                continue
            # Skip project pages
            if 'self-developing-agents.github.io' in url:
                continue
            urls.add(url)

    return sorted(urls)


def url_to_pdf_url(url):
    """Convert a paper page URL to its direct PDF URL."""
    url = url.strip()

    # arXiv abs -> pdf
    m = re.match(r'https?://arxiv\.org/abs/([\w.\-]+)(v\d+)?', url)
    if m:
        arxiv_id = m.group(1)
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    # arXiv pdf already
    if re.match(r'https?://arxiv\.org/pdf/[\w.\-]+\.pdf', url):
        return url

    # ACL anthology page -> pdf
    m = re.match(r'https?://aclanthology\.org/([\w.\-/]+?)/?$', url)
    if m:
        path = m.group(1).rstrip('/')
        return f"https://aclanthology.org/{path}.pdf"

    # ACL anthology pdf already
    if 'aclanthology.org' in url and url.endswith('.pdf'):
        return url

    # NeurIPS proceedings abstract page -> try pdf
    # https://proceedings.neurips.cc/paper_files/paper/2024/hash/XXX-Abstract-Conference.html
    m = re.match(
        r'https?://proceedings\.neurips\.cc/paper_files/paper/(\d{4})/hash/([\w]+)-Abstract-(Conference|Datasets_and_Benchmarks)\.html',
        url)
    if m:
        year, h, typ = m.group(1), m.group(2), m.group(3)
        return f"https://proceedings.neurips.cc/paper_files/paper/{year}/file/{h}-Paper-{typ}.pdf"

    # Older neurips format: https://proceedings.neurips.cc/paper/2023/hash/XXX-Abstract.html
    m = re.match(
        r'https?://proceedings\.neurips\.cc/paper/(\d{4})/hash/([\w]+)-Abstract\.html',
        url)
    if m:
        year, h = m.group(1), m.group(2)
        return f"https://proceedings.neurips.cc/paper/{year}/file/{h}-Paper.pdf"

    # OpenReview forum -> pdf
    m = re.match(r'https?://openreview\.net/forum\?id=([\w\-]+)', url)
    if m:
        return f"https://openreview.net/pdf?id={m.group(1)}"

    # Nature articles - may be paywalled, try anyway
    if 'nature.com/articles/' in url:
        return url + ".pdf"

    # ICML virtual poster - hard to get PDF directly, skip
    if 'icml.cc/virtual' in url:
        return None

    # NeurIPS virtual poster - hard to get PDF, skip
    if 'neurips.cc/virtual' in url:
        return None

    # AAAI OJS - try pdf
    if 'ojs.aaai.org' in url and '/article/view/' in url:
        return url.replace('/article/view/', '/article/view/') + '/pdf'

    # Huggingface datasets - not papers, skip
    if 'huggingface.co/datasets' in url:
        return None

    # Techrxiv
    if 'techrxiv.org' in url:
        return None  # Often complex

    # Default: return as-is if it ends with .pdf
    if url.endswith('.pdf'):
        return url

    # For other URLs, try appending .pdf as a guess
    return None


def safe_filename(url, original_url):
    """Generate a safe filename from URL."""
    # Try to extract arxiv ID
    m = re.search(r'arxiv\.org/(?:abs|pdf)/([\w.\-]+)', original_url)
    if m:
        return f"arxiv_{m.group(1)}.pdf"

    # ACL anthology
    m = re.search(r'aclanthology\.org/([\w.\-]+)', original_url)
    if m:
        return f"acl_{m.group(1)}.pdf"

    # NeurIPS hash
    m = re.search(r'neurips\.cc.*?/hash/([\w]+)', original_url)
    if m:
        return f"neurips_{m.group(1)[:16]}.pdf"

    # OpenReview
    m = re.search(r'openreview\.net/(?:forum|pdf)\?id=([\w\-]+)', original_url)
    if m:
        return f"openreview_{m.group(1)}.pdf"

    # Nature DOI
    m = re.search(r'nature\.com/articles/([\w.\-]+)', original_url)
    if m:
        return f"nature_{m.group(1)}.pdf"

    # Fallback: hash
    h = hashlib.md5(original_url.encode()).hexdigest()[:12]
    return f"paper_{h}.pdf"


def download_one(pdf_url, original_url, output_path):
    """Download a single PDF with retries."""
    if pdf_url is None:
        return False, "No PDF URL derivable", original_url

    if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
        return True, "Already exists", original_url

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/pdf,*/*',
    }

    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(pdf_url, headers=headers)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                content_type = resp.headers.get('Content-Type', '')
                data = resp.read()

            # Check if we got actual PDF content
            if len(data) < 1024:
                return False, f"Too small ({len(data)} bytes)", pdf_url

            if not data.startswith(b'%PDF') and 'pdf' not in content_type.lower():
                # Might be HTML redirect or error page
                return False, f"Not PDF (content-type: {content_type}, size: {len(data)})", pdf_url

            with open(output_path, 'wb') as f:
                f.write(data)
            return True, f"Downloaded ({len(data)} bytes)", pdf_url

        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False, f"HTTP 404", pdf_url
            if attempt == RETRIES - 1:
                return False, f"HTTP {e.code}", pdf_url
            time.sleep(2 ** attempt)
        except Exception as e:
            if attempt == RETRIES - 1:
                return False, f"Error: {str(e)[:100]}", pdf_url
            time.sleep(2 ** attempt)

    return False, "Max retries exceeded", pdf_url


def main():
    print(f"Reading {README_PATH}...")
    with open(README_PATH, 'r', encoding='utf-8') as f:
        text = f.read()

    urls = extract_paper_urls(text)
    print(f"Found {len(urls)} unique paper URLs")

    # Build download tasks
    tasks = []
    for original_url in urls:
        pdf_url = url_to_pdf_url(original_url)
        fname = safe_filename(pdf_url or original_url, original_url)
        output_path = os.path.join(OUTPUT_DIR, fname)
        tasks.append((pdf_url, original_url, output_path))

    # Filter out None pdf_urls but log them
    downloadable = [t for t in tasks if t[0] is not None]
    skipped = [t for t in tasks if t[0] is None]
    print(f"Downloadable: {len(downloadable)}, Skipped (no direct PDF): {len(skipped)}")

    results = []
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {}
        for pdf_url, original_url, output_path in downloadable:
            future = executor.submit(download_one, pdf_url, original_url, output_path)
            futures[future] = original_url

        for i, future in enumerate(as_completed(futures), 1):
            success, msg, used_url = future.result()
            original = futures[future]
            results.append((success, msg, original, used_url))
            if i % 20 == 0 or i == len(downloadable):
                print(f"  Progress: {i}/{len(downloadable)}")

    # Add skipped to results
    for _, original_url, _ in skipped:
        results.append((False, "No PDF URL derivable (skipped)", original_url, original_url))

    # Summary
    success_count = sum(1 for r in results if r[0])
    fail_count = len(results) - success_count
    print(f"\n=== Summary ===")
    print(f"Total: {len(results)}, Success: {success_count}, Failed: {fail_count}")

    # Write log
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write(f"Download Log - {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total: {len(results)}, Success: {success_count}, Failed: {fail_count}\n")
        f.write("=" * 80 + "\n\n")

        f.write("--- SUCCESSFUL ---\n")
        for success, msg, original, used in results:
            if success:
                f.write(f"[OK] {original}\n     -> {msg}\n     PDF: {used}\n\n")

        f.write("\n--- FAILED / SKIPPED ---\n")
        for success, msg, original, used in results:
            if not success:
                f.write(f"[FAIL] {original}\n       Reason: {msg}\n       Tried: {used}\n\n")

    print(f"Log written to {LOG_FILE}")

    # List downloaded files
    pdf_files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf')]
    print(f"\nPDF files in output directory: {len(pdf_files)}")


if __name__ == '__main__':
    main()
