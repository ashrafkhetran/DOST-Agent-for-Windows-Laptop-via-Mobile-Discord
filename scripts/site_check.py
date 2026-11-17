"""Quick technical SEO / QA check for one or many sites. Bounded output, no LLM needed.

  python site_check.py ashrafkhetran.com plumberyorkpa.com
  python site_check.py --file sites.txt            one domain/URL per line
  python site_check.py example.com --urls 30       also status-check the first 30 sitemap URLs
  python site_check.py example.com --json          machine-readable

Checks: status/redirects/final URL, HTTPS, response time, title (+length), meta description (+length),
H1 count, canonical, noindex, GA4 ID, robots.txt (+Sitemap line), sitemap.xml (URL count, follows index).
"""
import sys, re, json, time, argparse
from urllib.parse import urljoin, urlparse
import requests

UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36'}
T = 20


def get(url):
    t = time.time()
    try:
        r = requests.get(url, headers=UA, timeout=T, allow_redirects=True)
        return r, round(time.time() - t, 2), None
    except requests.RequestException as e:
        return None, round(time.time() - t, 2), type(e).__name__ + ': ' + str(e)[:120]


def tag(html, rx):
    m = re.search(rx, html, re.I | re.S)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else None


def sitemap_urls(url, depth=0):
    r, _, err = get(url)
    if not r or r.status_code != 200: return None, (err or (r.status_code if r else None))
    locs = re.findall(r'<loc>\s*([^<\s]+)\s*</loc>', r.text, re.I)
    if '<sitemapindex' in r.text[:2000].lower() and depth < 2:
        out = []
        for sm in locs[:20]:
            u, _ = sitemap_urls(sm, depth + 1); out += u or []
        return out, 200
    return locs, 200


def check(target, n_urls=0):
    url = target if target.startswith('http') else 'https://' + target.strip('/')
    res = {'site': target}
    r, secs, err = get(url)
    if not r:
        res['error'] = err; return res
    h = r.text
    res.update(status=r.status_code, final=r.url, redirects=len(r.history), https=r.url.startswith('https'), secs=secs)
    title = tag(h, r'<title[^>]*>(.*?)</title>')
    desc = tag(h, r'<meta[^>]+name=["\']description["\'][^>]*content=["\'](.*?)["\']') or tag(h, r'<meta[^>]+content=["\'](.*?)["\'][^>]*name=["\']description["\']')
    res.update(title=title, title_len=len(title or ''), desc_len=len(desc or ''), h1=len(re.findall(r'<h1[\s>]', h, re.I)),
               canonical=tag(h, r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\'](.*?)["\']'),
               noindex=bool(re.search(r'<meta[^>]+name=["\']robots["\'][^>]*noindex', h, re.I)) or 'noindex' in r.headers.get('X-Robots-Tag', ''),
               ga4=sorted(set(re.findall(r'G-[A-Z0-9]{6,12}', h)))[:3])
    base = '{0.scheme}://{0.netloc}/'.format(urlparse(r.url))
    rb, _, _ = get(urljoin(base, 'robots.txt'))
    res['robots'] = rb.status_code if rb else None
    sm_line = re.findall(r'(?im)^\s*sitemap:\s*(\S+)', rb.text) if rb is not None and rb.status_code == 200 else []
    res['robots_disallow_all'] = bool(rb is not None and rb.status_code == 200 and re.search(r'(?im)^\s*disallow:\s*/\s*$', rb.text))
    sm = sm_line[0] if sm_line else urljoin(base, 'sitemap.xml')
    urls, st = sitemap_urls(sm)
    res.update(sitemap=sm, sitemap_status=st, sitemap_urls=len(urls) if urls is not None else None)
    if n_urls and urls:
        bad = []
        for u in urls[:n_urls]:
            x, _, e = get(u)
            code = x.status_code if x else e
            if code != 200: bad.append(f'{u} -> {code}')
        res['url_check'] = f'{min(n_urls, len(urls))} checked, {len(bad)} not 200'
        res['bad_urls'] = bad[:15]
    issues = []
    if res['status'] != 200: issues.append(f"status {res['status']}")
    if not res['https']: issues.append('no https')
    if not title: issues.append('no title')
    elif not 15 <= res['title_len'] <= 65: issues.append(f"title len {res['title_len']}")
    if not res['desc_len']: issues.append('no meta desc')
    elif res['desc_len'] > 165: issues.append(f"desc len {res['desc_len']}")
    if res['h1'] != 1: issues.append(f"h1 x{res['h1']}")
    if res['noindex']: issues.append('NOINDEX')
    if res['robots_disallow_all']: issues.append('robots blocks all')
    if not res['ga4']: issues.append('no GA4 tag')
    if not res['sitemap_urls']: issues.append(f'sitemap {st}')
    if secs > 3: issues.append(f'slow {secs}s')
    if res.get('bad_urls'): issues.append(f"{len(res['bad_urls'])} bad sitemap URLs")
    res['issues'] = issues
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('sites', nargs='*'); ap.add_argument('--file'); ap.add_argument('--urls', type=int, default=0)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args()
    sites = list(a.sites)
    if a.file: sites += [l.strip() for l in open(a.file, encoding='utf-8') if l.strip() and not l.startswith('#')]
    if not sites: ap.error('give at least one site')
    out = [check(s, a.urls) for s in sites]
    if a.json: print(json.dumps(out, indent=1)); return
    for r in out:
        if 'error' in r: print(f"{r['site']}: ERROR {r['error']}"); continue
        print(f"{r['site']}: {r['status']} {r['secs']}s | title({r['title_len']}) {str(r['title'])[:70]!r} | desc {r['desc_len']} | h1 {r['h1']} | "
              f"GA4 {','.join(r['ga4']) or '-'} | robots {r['robots']} | sitemap {r['sitemap_urls']} urls" + (f" | {r['url_check']}" if 'url_check' in r else ''))
        print('   issues: ' + (', '.join(r['issues']) or 'none'))
        for b in r.get('bad_urls', []): print('   ' + b)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
