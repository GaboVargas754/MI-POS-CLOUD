from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from inventario.models import Categoria, PrecioProducto, Producto
from ventas.models import DetalleVenta, SesionCaja, Venta


class FlujoVentasTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cajero', password='testpass')
        self.user.user_permissions.add(Permission.objects.get(codename='acceder_ventas'))
        self.client.force_login(self.user)

        self.sesion = SesionCaja.objects.create(
            cajero=self.user,
            fondo_inicial=Decimal('50.00'),
            estado=True,
        )
        categoria = Categoria.objects.create(nombre='Bebidas')
        self.producto = Producto.objects.create(
            codigo_barras='750000000001',
            nombre='Agua',
            categoria=categoria,
            stock=5,
        )
        PrecioProducto.objects.create(
            producto=self.producto,
            costo=Decimal('5.00'),
            precio=Decimal('12.50'),
        )

    def test_agregar_al_carrito_usa_precio_relacionado(self):
        response = self.client.post(reverse('agregar_al_carrito', args=[self.producto.id]))

        self.assertEqual(response.status_code, 200)
        carrito = self.client.session['carrito']
        self.assertEqual(carrito[str(self.producto.id)]['precio'], '12.50')
        self.assertEqual(carrito[str(self.producto.id)]['subtotal'], '12.50')
        self.assertContains(response, '$12.50')

    def test_procesar_venta_asocia_sesion_y_descuenta_stock(self):
        self.client.post(reverse('agregar_al_carrito', args=[self.producto.id]))
        self.client.post(reverse('agregar_al_carrito', args=[self.producto.id]))

        response = self.client.post(reverse('procesar_venta'), {'pago_recibido': '30.00'})

        self.assertEqual(response.status_code, 200)
        venta = Venta.objects.get()
        self.assertEqual(venta.sesion, self.sesion)
        self.assertEqual(venta.total, Decimal('25.00'))
        self.assertEqual(venta.pago_recibido, Decimal('30.00'))
        self.assertEqual(venta.cambio, Decimal('5.00'))

        detalle = DetalleVenta.objects.get(venta=venta)
        self.assertEqual(detalle.precio_unitario, Decimal('12.50'))
        self.assertEqual(detalle.cantidad, 2)

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 3)
        self.assertEqual(self.client.session.get('carrito'), {})

    def test_cerrar_caja_calcula_ventas_de_la_sesion(self):
        Venta.objects.create(
            cajero=self.user,
            sesion=self.sesion,
            total=Decimal('25.00'),
            pago_recibido=Decimal('30.00'),
            cambio=Decimal('5.00'),
        )

        response = self.client.get(reverse('cerrar_caja'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['ventas_efectivo'], Decimal('25.00'))
        self.assertEqual(response.context['esperado_en_caja'], Decimal('75.00'))

    def test_pos_muestra_lector_nativo_con_enfoque(self):
        response = self.client.get(reverse('pantalla_pos'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'video-barras-pos')
        self.assertContains(response, 'BarcodeDetector')
        self.assertContains(response, 'enfocarCamaraPos')
        self.assertContains(response, 'btn-linterna-pos')
