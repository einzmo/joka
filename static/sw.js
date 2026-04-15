// static/sw.js
const CACHE_NAME = 'mymsce-v1';
const STATIC_CACHE = 'mymsce-static-v1';
const VIDEO_CACHE = 'mymsce-videos-v1';

const STATIC_ASSETS = [
    '/',
    '/static/js/history-manager.js',
    'https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(STATIC_CACHE).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('fetch', event => {
    // Video files - cache then network
    if (event.request.url.includes('/watch/') || event.request.url.includes('.mp4')) {
        event.respondWith(
            caches.open(VIDEO_CACHE).then(cache => {
                return fetch(event.request).then(response => {
                    cache.put(event.request, response.clone());
                    return response;
                }).catch(() => caches.match(event.request));
            })
        );
        return;
    }
    
    // Static assets - cache first
    event.respondWith(
        caches.match(event.request).then(response => {
            return response || fetch(event.request);
        })
    );
});