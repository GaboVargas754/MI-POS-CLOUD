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
    svg = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<rect width="512" height="512" rx="112" fill="#111827"/>
<rect x="96" y="128" width="320" height="256" rx="40" fill="#22c55e"/>
<rect x="128" y="168" width="256" height="64" rx="18" fill="#ecfdf5"/>
<circle cx="168" cy="300" r="22" fill="#052e16"/>
<circle cx="256" cy="300" r="22" fill="#052e16"/>
<circle cx="344" cy="300" r="22" fill="#052e16"/>
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
