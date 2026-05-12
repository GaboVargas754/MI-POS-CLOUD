from django.urls import path
from . import views

urlpatterns = [
    path('manifest.webmanifest', views.pwa_manifest, name='pwa_manifest'),
    path('pwa-icon.svg', views.pwa_icon, name='pwa_icon'),
    path('service-worker.js', views.service_worker, name='service_worker'),
    path('', views.portal_principal, name='portal_principal'),
]
