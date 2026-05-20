from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from configuraciones.models import PerfilUsuario, PuntoVenta, Tienda
from restaurante.models import Mesa


class ConfiguracionViewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='admin', password='testpass')
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=[
            'gestionar_usuarios',
            'gestionar_roles',
            'gestionar_tiendas',
            'editar_preferencias',
            'configurar_restaurante',
        ]))
        self.client.force_login(self.user)

    def test_formulario_rol_existe(self):
        response = self.client.get(reverse('nuevo_rol'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nuevo Rol')
        self.assertContains(response, 'data-role-permission-selector')
        self.assertContains(response, 'Disponibles')
        self.assertContains(response, 'Asignados')
        self.assertContains(response, 'data-role-permissions-source')

    def test_formulario_rol_requiere_permiso_granular(self):
        usuario = User.objects.create_user(username='usuarios', password='testpass')
        usuario.user_permissions.add(Permission.objects.get(codename='gestionar_usuarios'))
        self.client.force_login(usuario)

        response = self.client.get(reverse('nuevo_rol'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(reverse('portal_principal')))

    def test_formulario_ajustes_no_reutiliza_campos_de_usuario(self):
        response = self.client.get(reverse('ajustes_sistema'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Preferencias del Sistema')
        self.assertContains(response, 'Nombre de la Tienda')
        self.assertNotContains(response, 'Usuario Activo')

    def test_lista_usuarios_incluye_tarjetas_moviles(self):
        response = self.client.get(reverse('lista_usuarios'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'SISTEMA')
        self.assertContains(response, 'border-yellow-500')
        self.assertContains(response, 'nav-desktop-link')
        self.assertNotContains(response, 'mobile-menu')
        self.assertContains(response, 'md:hidden divide-y')
        self.assertContains(response, 'admin')
        self.assertContains(response, 'Sucursal Principal')

    def test_usuario_se_asigna_a_tienda_y_punto_venta(self):
        tienda = Tienda.objects.create(nombre='Sucursal Norte', codigo='NORTE')
        punto = PuntoVenta.objects.create(tienda=tienda, nombre='Caja Norte', codigo='CAJA-N')

        response = self.client.post(reverse('nuevo_usuario'), {
            'username': 'cajero-norte',
            'password': 'testpass123',
            'first_name': 'Cajero',
            'last_name': 'Norte',
            'email': 'norte@example.com',
            'is_active': 'on',
            'tienda': tienda.id,
            'punto_venta': punto.id,
        })

        self.assertRedirects(response, reverse('lista_usuarios'))
        usuario = User.objects.get(username='cajero-norte')
        self.assertEqual(usuario.perfil.tienda, tienda)
        self.assertEqual(usuario.perfil.punto_venta, punto)

    def test_lista_tiendas_y_formulario(self):
        response = self.client.get(reverse('lista_tiendas'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tiendas y Puntos de Venta')
        self.assertContains(response, 'Sucursal Principal')

        response = self.client.get(reverse('nueva_tienda'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nueva Tienda')

    def test_lista_mesas_y_formulario(self):
        Mesa.objects.create(nombre='Mesa 1', codigo='M1', zona='Terraza', capacidad=4)

        response = self.client.get(reverse('lista_mesas'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mesas de Restaurante')
        self.assertContains(response, 'Mesa 1')

        response = self.client.get(reverse('nueva_mesa'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nueva Mesa')

    def test_crear_mesa_desde_sistema(self):
        response = self.client.post(reverse('nueva_mesa'), {
            'nombre': 'Mesa 2',
            'codigo': 'M2',
            'zona': 'Interior',
            'capacidad': 6,
            'activa': 'on',
        })

        self.assertRedirects(response, reverse('lista_mesas'))
        mesa = Mesa.objects.get(codigo='M2')
        self.assertEqual(mesa.nombre, 'Mesa 2')
        self.assertEqual(mesa.zona, 'Interior')
        self.assertEqual(mesa.capacidad, 6)
        self.assertTrue(mesa.activa)

    def test_mesas_requiere_permiso_configurar_restaurante(self):
        usuario = User.objects.create_user(username='sin-mesas', password='testpass')
        usuario.user_permissions.add(Permission.objects.get(codename='gestionar_usuarios'))
        self.client.force_login(usuario)

        response = self.client.get(reverse('lista_mesas'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(reverse('portal_principal')))
