from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from core.utils import get_config_context

@login_required
def portal_principal(request):
    return render(request, 'core/portal.html', get_config_context('Portal Principal', 'border-gray-500'))


def pwa_manifest(request):
    return JsonResponse({
        'name': 'Sistema POS',
        'short_name': 'POS',
        'description': 'Punto de venta móvil para ventas, inventario y caja.',
        'start_url': reverse('portal_principal'),
        'scope': '/',
        'display': 'standalone',
        'background_color': '#111827',
        'theme_color': '#111827',
        'orientation': 'portrait-primary',
        'icons': [
            {
                'src': reverse('pwa_icon'),
                'sizes': '192x192',
                'type': 'image/svg+xml',
                'purpose': 'any maskable',
            },
            {
                'src': reverse('pwa_icon'),
                'sizes': '512x512',
                'type': 'image/svg+xml',
                'purpose': 'any maskable',
            },
        ],
    }, content_type='application/manifest+json')


def pwa_icon(request):
    svg = '''<svg width="512" height="512" viewBox="0 0 512 512" fill="none" xmlns="http://www.w3.org/2000/svg">
  <rect width="512" height="512" rx="90" fill="#111827"/>

  <path
    d="M122 188H158L190 312C194 328 208 340 225 340H354"
    stroke="#22C55E"
    stroke-width="24"
    stroke-linecap="round"
    stroke-linejoin="round"
  />

  <path
    d="M196 286H354C384 286 408 262 408 232C408 204 386 181 358 179C348 142 314 116 274 116C232 116 197 146 190 186"
    stroke="#22C55E"
    stroke-width="24"
    stroke-linecap="round"
    stroke-linejoin="round"
  />

  <path
    d="M210 340H360"
    stroke="#22C55E"
    stroke-width="10"
    stroke-linecap="round"
  />

  <circle cx="226" cy="386" r="20" stroke="#22C55E" stroke-width="22"/>
  <circle cx="338" cy="386" r="20" stroke="#22C55E" stroke-width="22"/>
</svg>'''
    return HttpResponse(svg, content_type='image/svg+xml')


def service_worker(request):
    script = '''const CACHE_NAME = 'pos-shell-v1';
const SHELL_URLS = ['/', '/manifest.webmanifest'];

self.addEventListener('install', event => {
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(SHELL_URLS)));
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => Promise.all(keys.filter(key => key !== CACHE_NAME).map(key => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  event.respondWith(
    fetch(request).then(response => {
      const copy = response.clone();
      caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
      return response;
    }).catch(() => caches.match(request))
  );
});
'''
    return HttpResponse(script, content_type='application/javascript')
