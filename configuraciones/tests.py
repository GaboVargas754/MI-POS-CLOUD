from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse


class ConfiguracionViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='testpass')
        self.user.user_permissions.add(Permission.objects.get(codename='acceder_configuraciones'))
        self.client.force_login(self.user)

    def test_formulario_rol_existe(self):
        response = self.client.get(reverse('nuevo_rol'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nuevo Rol')

    def test_formulario_ajustes_no_reutiliza_campos_de_usuario(self):
        response = self.client.get(reverse('ajustes_sistema'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Preferencias del Sistema')
        self.assertContains(response, 'Nombre de la Tienda')
        self.assertNotContains(response, 'Usuario Activo')
