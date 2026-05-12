from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse


class ProductoFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='inventario', password='testpass')
        self.user.user_permissions.add(Permission.objects.get(codename='acceder_inventario'))
        self.client.force_login(self.user)

    def test_formulario_producto_muestra_escaner_de_codigo(self):
        response = self.client.get(reverse('nuevo_producto'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'abrirCamaraProducto')
        self.assertContains(response, 'modal-escaner-producto')
        self.assertContains(response, 'Escanear Código')
        self.assertContains(response, 'video-barras-producto')
        self.assertContains(response, 'BarcodeDetector')
        self.assertContains(response, 'enfocarCamaraProducto')
        self.assertContains(response, 'btn-linterna-producto')
