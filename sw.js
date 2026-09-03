/* Ponhada's Clay League — Service Worker (PWA)
   - App shell em cache (abre offline)
   - Dados do ranking sempre da rede quando online (cai pro cache offline)
   - NUNCA guarda respostas de erro (404 etc.) — evita "prender" foto que ainda não existia
   - Bump CACHE ao mudar o shell (o activate limpa os caches antigos) */
const CACHE = "ponhadas-v2";
const SHELL = [
  "/", "/index.html", "/manifest.webmanifest", "/logo.png",
  "/apple-touch-icon.png",
  "/icons/icon-192.png", "/icons/icon-512.png", "/icons/icon-maskable-512.png"
];

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys()
      .then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// só guarda no cache respostas boas (200, same-origin) — nunca 404/erro
function putIfOk(req, res) {
  if (res && res.ok && res.type !== "opaque") {
    const cp = res.clone();
    caches.open(CACHE).then(c => c.put(req, cp));
  }
  return res;
}

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Dados do ranking: rede primeiro (sempre atualizado), cache como reserva offline
  if (url.pathname.startsWith("/data/")) {
    e.respondWith(
      fetch(req).then(r => putIfOk(req, r)).catch(() => caches.match(req))
    );
    return;
  }

  // Navegação: rede primeiro, cai pro index em cache quando offline
  if (req.mode === "navigate") {
    e.respondWith(fetch(req).catch(() => caches.match("/index.html")));
    return;
  }

  // Demais arquivos (fotos, ícones, etc.): cache primeiro, senão rede (e guarda só se OK)
  e.respondWith(
    caches.match(req).then(c => c || fetch(req).then(r => putIfOk(req, r)))
  );
});
