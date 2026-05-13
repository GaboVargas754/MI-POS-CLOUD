from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse


class PwaAndMobileNavigationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='movil', password='testpass')
        self.user.user_permissions.add(
            Permission.objects.get(codename='operar_pos'),
            Permission.objects.get(codename='ver_estadisticas'),
            Permission.objects.get(codename='ver_inventario'),
            Permission.objects.get(codename='gestionar_usuarios'),
        )

    def test_manifest_expone_configuracion_pwa(self):
        response = self.client.get(reverse('pwa_manifest'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/manifest+json')
        self.assertEqual(response.json()['display'], 'standalone')
        self.assertEqual(response.json()['start_url'], reverse('portal_principal'))

    def test_service_worker_se_entrega_como_javascript(self):
        response = self.client.get(reverse('service_worker'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/javascript')
        self.assertContains(response, 'CACHE_NAME')

    def test_pwa_icon_usa_logo_personalizado(self):
        response = self.client.get(reverse('pwa_icon'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')
        self.assertContains(response, '#111827')
        self.assertContains(response, '#22C55E')
        self.assertContains(response, 'M122 188H158')

    def test_portal_incluye_navegacion_inferior_movil(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('portal_principal'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'sm:hidden fixed bottom-0')
        self.assertContains(response, 'POS')
        self.assertContains(response, 'Estadísticas')
        self.assertContains(response, 'Inventario')
        self.assertContains(response, 'Sistema')
        self.assertContains(response, 'rel="icon"')
        self.assertContains(response, reverse('pwa_icon'))
        self.assertContains(response, reverse('pantalla_pos'))
        self.assertContains(response, reverse('dashboard'))
