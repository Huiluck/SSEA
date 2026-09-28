#!/usr/bin/env python3
"""Generate download manifest JSON for PowerShell to consume."""

import os
import re
import json
import hashlib

README_PATH = r"C:\MyDocs\AGI\README.md"
OUTPUT_DIR = r"C:\MyDocs\AGI\SSEA\docs\papers"
MANIFEST = os.path.join(OUTPUT_DIR, "_manifest.json")

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
    m = re.match(r'https?://arxiv\.org/abs/([\w.\-]+)(v\d+)?', url)
    if m:
        return f"https://arxiv.org/pdf/{m.group(1)}.pdf"
    if re.match(r'https?://arxiv\.org/pdf/[\w.\-]+\.pdf', url):
        return url
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
    m = re.match(r'https?://openreview\.net/forum\?id=([\w\-]+)', url)
    if m:
        return f"https://openreview.net/pdf?id={m.group(1)}"
    if 'nature.com/articles/' in url and not url.endswith('.pdf'):
        return url + ".pdf"
    if 'icml.cc/virtual' in url or 'neurips.cc/virtual' in url:
        return None
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
    h = hashlib.md5(original_url.encode()).hexdigest()[:12]
    return f"paper_{h}.pdf"


def main():
    existing = set(f for f in os.listdir(OUTPUT_DIR) if f.endswith('.pdf'))
    print(f"Already downloaded: {len(existing)} files")

    with open(README_PATH, 'r', encoding='utf-8') as f:
        text = f.read()

    urls = extract_paper_urls(text)
    print(f"Total paper URLs: {len(urls)}")

    manifest = []
    for original_url in urls:
        fname = safe_filename(original_url)
        if fname in existing:
            continue
        pdf_url = url_to_pdf_url(original_url)
        if pdf_url is None:
            continue
        manifest.append({
            "pdf_url": pdf_url,
            "original_url": original_url,
            "filename": fname,
            "is_arxiv": "arxiv.org" in pdf_url
        })

    print(f"To download: {len(manifest)} papers")
    arxiv_count = sum(1 for m in manifest if m["is_arxiv"])
    print(f"  arXiv: {arxiv_count}, other: {len(manifest) - arxiv_count}")

    with open(MANIFEST, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    print(f"Manifest written to {MANIFEST}")


if __name__ == '__main__':
    main()
