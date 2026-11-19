// 离线缓存：网页本身先联网取最新（4 秒取不到就用缓存）；Google AI 的请求不经过这里
const V = "ec-d0711944e5";
const SHELL = ["./", "index.html", "manifest.webmanifest", "icon-180.png", "icon-192.png", "icon-512.png"];
self.addEventListener("install", e => { e.waitUntil(caches.open(V).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())); });
self.addEventListener("activate", e => { e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))).then(() => self.clients.claim())); });
self.addEventListener("fetch", e => {
  const req = e.request; const u = new URL(req.url);
  if (req.method !== "GET" || u.origin !== location.origin) return;
  const key = u.pathname.endsWith("/feeds.json") ? new Request(u.origin + u.pathname) : req;
  e.respondWith((async () => {
    const c = await caches.open(V);
    const net = fetch(req).then(r => { if (r.ok) c.put(key, r.clone()); return r; });
    const timeout = new Promise(r => setTimeout(() => r(null), 4000));
    try { const r = await Promise.race([net, timeout]); if (r) return r; } catch (err) {}
    const hit = await c.match(key, { ignoreSearch: true });
    if (hit) return hit;
    return net;
  })());
});
