/* Service worker do monitor de compras.
   Estratégia: rede primeiro, cache como reserva — assim o app abre sem internet
   e sempre mostra a base mais recente quando há conexão. */
const CACHE = 'monitor-compras-v4';
const ARQUIVOS = ['./', './index.html', './dados.js', './historico.js', './manifest.webmanifest',
                  './icone.svg', './icone-192.png', './icone-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(ARQUIVOS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

/* A página em si nunca vem do cache quando há rede: evita ficar preso em versão velha. */
self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  if (new URL(e.request.url).search) return;   // checagem de base nova vai direto à rede
  e.respondWith(
    fetch(e.request)
      .then(resp => {
        const copia = resp.clone();
        caches.open(CACHE).then(c => c.put(e.request, copia)).catch(() => {});
        return resp;
      })
      .catch(() => caches.match(e.request).then(r => r || caches.match('./index.html')))
  );
});
