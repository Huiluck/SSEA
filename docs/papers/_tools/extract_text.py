#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Extract plain text from a PDF in docs/papers for card writing.

Usage:
    python extract_text.py "<pdf file name or relative path>" [--max-chars N] [--head N]

Prints page-delimited text with page numbers so that quotes can be cited by page.
"""
import argparse
import os
import sys

from pypdf import PdfReader

PAPER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def resolve(name: str) -> str:
    if os.path.isabs(name) and os.path.exists(name):
        return name
    cand = os.path.join(PAPER_DIR, name)
    if os.path.exists(cand):
        return cand
    if not name.lower().endswith(".pdf"):
        cand2 = cand + ".pdf"
        if os.path.exists(cand2):
            return cand2
    # fuzzy
    key = name.lower()
    for f in sorted(os.listdir(PAPER_DIR)):
        if f.lower().endswith(".pdf") and key in f.lower():
            return os.path.join(PAPER_DIR, f)
    raise SystemExit("PDF not found: %s" % name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pdf")
    ap.add_argument("--max-chars", type=int, default=200000)
    ap.add_argument("--head", type=int, default=0, help="only first N pages")
    ap.add_argument("--pages", default="", help="e.g. 1-8,12")
    args = ap.parse_args()

    path = resolve(args.pdf)
    reader = PdfReader(path)
    n = len(reader.pages)
    idxs = list(range(n))
    if args.pages:
        sel = []
        for part in args.pages.split(","):
            if "-" in part:
                a, b = part.split("-")
                sel.extend(range(int(a) - 1, min(int(b), n)))
            else:
                sel.append(int(part) - 1)
        idxs = sel
    if args.head:
        idxs = idxs[: args.head]

    out = []
    total = 0
    for i in idxs:
        try:
            t = reader.pages[i].extract_text() or ""
        except Exception as e:  # pragma: no cover
            t = "[extract error: %s]" % e
        t = "\n".join(ln.rstrip() for ln in t.splitlines() if ln.strip())
        out.append("\n===== PAGE %d =====\n%s" % (i + 1, t))
        total += len(t)
        if total > args.max_chars:
            out.append("\n[TRUNCATED at %d chars]" % total)
            break
    sys.stdout.write("FILE: %s\nPAGES: %d\n" % (os.path.basename(path), n))
    sys.stdout.write("\n".join(out))


if __name__ == "__main__":
    main()
