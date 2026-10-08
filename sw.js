// Keeps the app's page and icons on the phone so it opens instantly; the page itself is refreshed from the network when possible.
const SHELL = 'th-shell-v3';
self.addEventListener('install', e => { e.waitUntil(caches.open(SHELL).then(c => c.addAll(['./', 'index.html', 'icon-192.png', 'icon-512.png', 'apple-touch-icon.png']))); self.skipWaiting(); });
self.addEventListener('activate', e => e.waitUntil(self.clients.claim()));
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;                       // data calls go straight to the network
  // Always ask GitHub for the latest page (its 10-minute cache would otherwise keep an old version on the phone).
  e.respondWith(fetch(e.request, { cache: 'no-cache' }).then(r => { const copy = r.clone(); caches.open(SHELL).then(c => c.put(e.request, copy)); return r; })
    .catch(() => caches.match(e.request).then(r => r || caches.match('index.html'))));
});
