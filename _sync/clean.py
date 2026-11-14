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

def unwrap(html: str) -> str:
    start = html.find('<!DOCTYPE html>')
    if start == -1:
        low = html.lower(); f = low.find('<!doctype html>'); s = low.find('<!doctype html>', f + 1)
        start = s if s != -1 else (f if f != -1 else 0)
    inner = html[start:]
    pos = inner.rfind('</body></html>')
    if pos != -1:
        inner = inner[:pos]
    inner = inner.rstrip() + '\n'
    if not inner.rstrip().endswith('</html>'):
        inner = inner.rstrip() + '\n</html>\n'
    return inner

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
    html = re.sub(r'<style>:root\{color-scheme:light\}[\s\S]*?</style>', '', html, count=1)
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
    ok = (out.lstrip().startswith('<!DOCTYPE html>')
          and '<html lang=' in out
          and low.count('<html') == 1
          and low.count('<body') == 1
          and custom == 0
          and len(out) >= 20000
          and '<title>' in low
          and 'level up fest' in low)
    print('clean:', dst, '| bytes:', len(out), '| <html>:', low.count('<html'),
          '| <body>:', low.count('<body'), '| custom-tags:', custom, '| ok:', ok)
    sys.exit(0 if ok else 2)

if __name__ == '__main__':
    main()
