/* 차 노트를 신호가 약한 곳에서도 열 수 있게 한다.
   - 화면(index.html 등): 먼저 인터넷에서 새것을 받고, 안 되면 담아 둔 것을 보여 준다(새 내용이 늘 먼저).
   - 사진(assets/): 한 번 본 사진은 담아 둔 것을 바로 보여 준다(사진 파일은 이름이 같으면 내용도 같다). */
const CACHE = 'tea-note-v1';
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;
  const keep = res => { if (res && res.ok) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); } return res; };
  if (url.pathname.includes('/assets/')) {
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(keep)));
  } else {
    e.respondWith(fetch(req).then(keep).catch(() => caches.match(req, {ignoreSearch: true}).then(hit => hit || caches.match('./', {ignoreSearch: true}))));
  }
});
