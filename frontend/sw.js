/* FitWell Journal — Service Worker
 * 缓存应用外壳与 vendor 静态资源，cache-first 策略。
 * API 请求（/api/）不缓存，始终走网络。
 * 版本号变更时更新 CACHE_VERSION 以触发缓存刷新。
 */
'use strict';

const CACHE_VERSION = 'fitwell-shell-v0.1.0';

// 应用外壳静态资源清单
const SHELL_ASSETS = [
  './',
  'index.html',
  'css/styles.css',
  'js/api.js',
  'js/charts.js',
  'js/app.js',
  'manifest.webmanifest',
  'vendor/react.production.min.js',
  'vendor/react-dom.production.min.js',
  'vendor/htm.umd.js',
  'icons/icon-192.png',
  'icons/icon-512.png'
];

// 安装：预缓存应用外壳
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) => cache.addAll(SHELL_ASSETS))
  );
  self.skipWaiting();
});

// 激活：清理旧版本缓存
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys.filter((key) => key !== CACHE_VERSION).map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

// fetch：同源静态资源 cache-first；API 与跨域请求直连网络
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // API 请求不缓存
  if (url.pathname.startsWith('/api/')) return;
  // 只处理同源 GET 请求
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) return;

  event.respondWith(
    caches.match(event.request).then((cached) => {
      if (cached) return cached;
      return fetch(event.request).then((response) => {
        // 成功响应写入缓存，供下次离线使用
        if (response && response.status === 200 && response.type === 'basic') {
          const copy = response.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put(event.request, copy));
        }
        return response;
      });
    })
  );
});
