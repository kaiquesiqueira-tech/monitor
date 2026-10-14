/* Service worker do monitor de compras.

   O app abre do cache e sai andando; a rede é consultada em paralelo e o cache
   é atualizado para a próxima vez. Assim a abertura é instantânea, inclusive
   sem internet, e a base nova chega sozinha porque a própria página verifica o
   dados.js a cada poucos segundos e troca os dados sem recarregar. */

const CACHE = 'monitor-compras-v5';
const SHELL = ['./', './index.html', './historico.js', './manifest.webmanifest',
               './icone.svg', './icone-180.png', './icone-192.png', './icone-512.png'];
const BASE = ['./dados.js', './pulso.json'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE)
      .then(c => Promise.all(SHELL.concat(BASE).map(u => c.add(u).catch(() => {}))))
      .then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

function guardar(req, resp) {
  if (resp && resp.ok) {
    const copia = resp.clone();
    caches.open(CACHE).then(c => c.put(req, copia)).catch(() => {});
  }
  return resp;
}

self.addEventListener('fetch', e => {
  if (e.request.method !== 'GET') return;
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;        // fontes e afins seguem direto
  if (url.search) return;                            // as checagens da página vão à rede

  const ehBase = /dados\.js$|pulso\.json$/.test(url.pathname);

  if (ehBase) {                                      // base: rede primeiro, cache de reserva
    e.respondWith(
      fetch(e.request).then(r => guardar(e.request, r))
        .catch(() => caches.match(e.request)));
    return;
  }

  /* resto: devolve o cache na hora e busca a versão nova por trás */
  e.respondWith(
    caches.match(e.request).then(guardado => {
      const rede = fetch(e.request).then(r => guardar(e.request, r)).catch(() => null);
      return guardado || rede.then(r => r || caches.match('./index.html'));
    }));
});
