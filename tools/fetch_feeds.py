# 定时抓新闻（GitHub Actions 运行）：RSS 列表 + 每篇文章的正文段落 → feeds.json
# 浏览器不能直接读 BBC / RNZ（跨域限制），所以由这里代读。只用 Python 标准库。
import concurrent.futures as cf, html, json, re, sys, time, urllib.request
from datetime import datetime, timezone

FEEDS = [
    "https://feeds.bbci.co.uk/news/world/rss.xml", "https://www.rnz.co.nz/rss/world.xml",
    "https://feeds.bbci.co.uk/news/business/rss.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    "https://feeds.bbci.co.uk/sport/rss.xml", "https://www.rnz.co.nz/rss/sport.xml",
    "https://feeds.bbci.co.uk/news/entertainment_and_arts/rss.xml",
    "https://feeds.bbci.co.uk/news/health/rss.xml",
    "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml",
    "https://www.rnz.co.nz/rss/national.xml",
    "https://www.kiwikidsnews.co.nz/feed/",
]
UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Mobile/15E148 Safari/604.1"
JUNK = re.compile(r"cookie|subscribe|newsletter|copyright|©|sign up|download the app", re.I)

def get(url, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-NZ,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")

def strip(s):
    s = re.sub(r"<!\[CDATA\[([\s\S]*?)\]\]>", r"\1", s or "")
    s = html.unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()

def parse_rss(xml):
    items = []
    for m in re.finditer(r"<item[\s>][\s\S]*?</item>", xml):
        b = m.group(0)
        g = lambda t: (lambda x: strip(x.group(1)) if x else "")(re.search(rf"<{t}[^>]*>([\s\S]*?)</{t}>", b))
        title = g("title")
        if not title: continue
        items.append({"title": title, "link": g("link"), "desc": g("description")[:300]})
        if len(items) >= 15: break
    return items

def article(url):
    try:
        page = get(url)
    except Exception as e:
        return url, None
    paras, total = [], 0
    for m in re.finditer(r"<p[^>]*>([\s\S]*?)</p>", page):
        t = strip(m.group(1))
        if len(t) > 60 and not JUNK.search(t):
            paras.append(t); total += len(t)
            if total > 3600: break
    return url, paras

def main(out):
    feeds, links = {}, []
    for u in FEEDS:
        try:
            feeds[u] = parse_rss(get(u))
            links += [i["link"] for i in feeds[u] if i["link"]]
            print("feed", len(feeds[u]), u)
        except Exception as e:
            print("FEED FAIL", u, e, file=sys.stderr)
    articles = {}
    with cf.ThreadPoolExecutor(8) as ex:
        for url, paras in ex.map(article, dict.fromkeys(links)):
            if paras: articles[url] = paras
    print("articles", len(articles), "of", len(set(links)))
    if not any(feeds.values()):
        sys.exit("no feeds at all; keep the old file")
    data = {"updated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "feeds": feeds, "articles": articles}
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "feeds.json")
