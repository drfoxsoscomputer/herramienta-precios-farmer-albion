const CACHE = 'albion-helper-v1';
const URLS = ['/', '/manifest.json', '/config', '/pesca', '/recursos', '/salsas', '/buscar'];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(URLS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  if (e.request.url.includes('render.albiononline.com')) return;
  if (e.request.url.includes('/qr')) return;
  e.respondWith(
    fetch(e.request).catch(() => caches.match(e.request))
  );
});