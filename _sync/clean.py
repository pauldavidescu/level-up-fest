#!/usr/bin/env python3
"""Clean a Claude-artifact-read HTML file for deployment to levelupfest.com.

Two jobs:
 1) UNWRAP claude.ai's skeleton (keep the inner authored document).
 2) SANITIZE browser-extension + artifact-runtime cruft that the in-page editor
    bakes in when it clones the live DOM on publish (Grammarly / Superhuman /
    ChatGPT-sidebar nodes, their data-* attributes, claude runtime styles).

Rule: our authored pages use NO custom (hyphenated) HTML elements, so ANY
<word-word ...> tag is injected and gets removed.

Usage: python3 clean.py <raw-artifact-html> <cleaned-out-html>
Exit code 0 on success; prints a one-line report. Exits non-zero if the result
fails a basic structural sanity check (so callers can abort before deploying).
"""
import re, sys

# Normalize the artifact-read document WITHOUT ripping out structural tags.
# These pages come in two shapes: (a) a complete <!DOCTYPE html><html>…</html>, and
# (b) a FRAGMENT (title/meta/styles + body markup) that leans on the claude skeleton for its
# <html>/<head>/<body>. In both cases the skeleton (when present) supplies exactly one
# <html>/<head>/<body>, and its reset styles / wrapper elements are stripped later by
# sanitize(). So unwrap does the minimum: drop anything before the first doctype, and
# collapse a DUPLICATED trailing close the skeleton sometimes adds. It must never key off a
# bare '<!DOCTYPE html>' elsewhere (e.g. the editor JS literal) — that was the old bug.
def unwrap(html: str) -> str:
    i = html.lower().find('<!doctype html>')
    if i > 0:
        html = html[i:]
    low = html.lower()
    # Two shapes come back from the artifact read:
    #  (a) skeleton + FRAGMENT  → one <html> total (the skeleton's). Keep the whole thing;
    #      sanitize() strips the skeleton's reset styles. Our head elements sit in <body>,
    #      which browsers tolerate.
    #  (b) skeleton + COMPLETE inner doc → two <html>. Keep ONLY the inner document.
    opens = [m.start() for m in re.finditer(r'<html[\s>]', low)]
    if len(opens) >= 2:
        second = opens[1]
        ds = low.rfind('<!doctype html>', 0, second)   # doctype just before the 2nd <html>
        start = ds if ds != -1 else second
        html = html[start:]
        j = html.lower().find('</html>')                # inner doc's own close
        if j != -1:
            html = html[:j + len('</html>')]
    # Collapse any doubled trailing close the skeleton may add.
    html = re.sub(r'</html>\s*</body>\s*</html>\s*\Z', '</html>', html, flags=re.I)
    return html.rstrip() + '\n'

CS = re.compile(r'<[a-z][a-z0-9]*-[a-z0-9-]+\b[^>]*/>', re.I)
CI = re.compile(r'<([a-z][a-z0-9]*-[a-z0-9-]+)\b[^>]*>[^<]*?</\1\s*>', re.I)
CA = re.compile(r'</?[a-z][a-z0-9]*-[a-z0-9-]+\b[^>]*>', re.I)

def sanitize(html: str) -> str:
    html = CS.sub('', html)
    prev = None
    while prev != html:
        prev = html
        html = CI.sub('', html)
    html = CA.sub('', html)
    html = re.sub(r'\s+data-new-gr-[a-z0-9-]+(="[^"]*")?', '', html)
    html = re.sub(r'\s+data-gr-[a-z0-9-]+(="[^"]*")?', '', html)
    html = re.sub(r'\s+data-grammarly-[a-z0-9-]+(="[^"]*")?', '', html)
    html = re.sub(r'\s+data-gpts?-[a-z0-9-]+(="[^"]*")?', '', html)
    # Remove EVERY claude skeleton reset <style> (they can duplicate across publish cycles,
    # and come in variants: ":root{color-scheme:light}…" or ":root{color-scheme:light;box-sizing:…}…").
    html = re.sub(r'<style>:root\{color-scheme:light[;}][\s\S]*?</style>', '', html)
    html = re.sub(r'<style>\s*artifact-[\s\S]*?</style>', '', html)
    html = re.sub(r'<style>\s*</style>', '', html)
    html = re.sub(r'(<body\b[^>]*?)\s+class=""', r'\1', html)
    return html

def main():
    src, dst = sys.argv[1], sys.argv[2]
    raw = open(src, encoding='utf-8').read()
    out = sanitize(unwrap(raw))
    open(dst, 'w', encoding='utf-8').write(out)
    low = out.lower()
    custom = len(CA.findall(out))
    # Site-agnostic structural sanity: one well-formed document, no extension cruft,
    # a title, and non-trivial size. (Do NOT hard-code brand strings — this runs on any site.)
    ok = (out.lstrip().lower().startswith('<!doctype html>')
          and low.count('<html') == 1
          and low.count('<body') == 1
          and custom == 0
          and len(out) >= 10000
          and '<title>' in low)
    print('clean:', dst, '| bytes:', len(out), '| <html>:', low.count('<html'),
          '| <body>:', low.count('<body'), '| custom-tags:', custom, '| ok:', ok)
    sys.exit(0 if ok else 2)

if __name__ == '__main__':
    main()
