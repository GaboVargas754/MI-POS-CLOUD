from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from configuraciones.models import PerfilUsuario, Tienda
from inventario.models import Categoria, MovimientoInventario, PrecioProducto, Producto
from restaurante import services
from restaurante.models import Mesa, Pedido, PedidoItem, ProductoPreparacion
from ventas.models import DetalleVenta, PagoVenta, SesionCaja, Venta


class RestauranteServicesTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='mesero', password='secret')
        self.tienda = Tienda.objects.create(nombre='Sucursal', codigo='SUC')
        PerfilUsuario.objects.create(usuario=self.user, tienda=self.tienda)
        self.mesa = Mesa.objects.create(nombre='Mesa 1', codigo='M1')
        categoria = Categoria.objects.create(nombre='Comida')
        self.producto = Producto.objects.create(
            codigo_barras='P001',
            nombre='Taco',
            categoria=categoria,
            stock=10,
            stock_minimo=2,
        )
        PrecioProducto.objects.create(producto=self.producto, costo=Decimal('4.00'), precio=Decimal('10.00'))

    def abrir_sesion(self):
        return SesionCaja.objects.create(
            cajero=self.user,
            tienda=self.tienda,
            fondo_inicial=Decimal('100.00'),
            estado=True,
        )

    def dar_permisos(self, *codenames):
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=codenames))

    def crear_pedido_con_item(self):
        pedido = services.crear_pedido(
            tipo='MESA',
            usuario=self.user,
            tienda=self.tienda,
            mesa_id=self.mesa.id,
        )
        item = services.agregar_item_borrador(
            pedido=pedido,
            producto_id=self.producto.id,
            cantidad=2,
            usuario=self.user,
        )
        return pedido, item

    def test_enviar_a_cocina_descuenta_stock_y_cobrar_no_descuenta_de_nuevo(self):
        pedido, _ = self.crear_pedido_con_item()
        self.abrir_sesion()

        services.enviar_a_cocina(pedido=pedido, usuario=self.user)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)
        self.assertEqual(MovimientoInventario.objects.filter(tipo=MovimientoInventario.Tipo.VENTA).count(), 1)

        venta = services.cobrar_pedido(
            pedido=pedido,
            usuario=self.user,
            metodo_pago='EFE',
            pago_recibido=Decimal('20.00'),
        )

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)
        self.assertEqual(venta.total, Decimal('20.00'))
        self.assertEqual(DetalleVenta.objects.filter(venta=venta).count(), 1)
        self.assertEqual(MovimientoInventario.objects.filter(tipo=MovimientoInventario.Tipo.VENTA).count(), 1)
        self.assertEqual(list(venta.pagos.values_list('metodo_pago', 'monto')), [('EFE', Decimal('20.00'))])

    def test_cobrar_pedido_guarda_propina_y_pago_mixto(self):
        pedido, _ = self.crear_pedido_con_item()
        self.abrir_sesion()
        services.enviar_a_cocina(pedido=pedido, usuario=self.user)

        venta = services.cobrar_pedido(
            pedido=pedido,
            usuario=self.user,
            metodo_pago='MIX',
            porcentaje_propina=Decimal('10.00'),
            pago_efectivo=Decimal('5.00'),
            pago_tarjeta=Decimal('17.00'),
        )

        self.assertEqual(venta.subtotal, Decimal('20.00'))
        self.assertEqual(venta.propina, Decimal('2.00'))
        self.assertEqual(venta.porcentaje_propina, Decimal('10.00'))
        self.assertEqual(venta.total, Decimal('22.00'))
        self.assertEqual(venta.metodo_pago, 'MIX')
        self.assertEqual(list(venta.pagos.values_list('metodo_pago', 'monto')), [
            ('EFE', Decimal('5.00')),
            ('TAR', Decimal('17.00')),
        ])

    def test_cobrar_rechaza_items_borrador(self):
        pedido, _ = self.crear_pedido_con_item()
        self.abrir_sesion()

        with self.assertRaisesMessage(ValidationError, 'Envía o elimina los productos pendientes antes de cobrar.'):
            services.cobrar_pedido(
                pedido=pedido,
                usuario=self.user,
                metodo_pago='EFE',
                pago_recibido=Decimal('20.00'),
            )

        self.assertFalse(Venta.objects.exists())

    def test_cancelar_item_pendiente_reintegra_stock(self):
        pedido, item = self.crear_pedido_con_item()
        services.enviar_a_cocina(pedido=pedido, usuario=self.user)
        item.refresh_from_db()

        services.eliminar_o_cancelar_item(item=item, usuario=self.user, motivo='Error de captura')

        self.producto.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)
        self.assertEqual(item.estado, PedidoItem.Estado.CANCELADO)
        self.assertTrue(item.reintegro_stock)
        self.assertEqual(MovimientoInventario.objects.filter(tipo=MovimientoInventario.Tipo.CANCELACION).count(), 1)

    def test_producto_que_no_va_a_kds_queda_listo_al_enviar(self):
        ProductoPreparacion.objects.create(producto=self.producto, enviar_a_kds=False)
        pedido, item = self.crear_pedido_con_item()

        services.enviar_a_cocina(pedido=pedido, usuario=self.user)

        pedido.refresh_from_db()
        item.refresh_from_db()
        self.assertEqual(item.estado, PedidoItem.Estado.LISTO)
        self.assertEqual(pedido.estado, Pedido.Estado.LISTO)

    def test_actualizar_estado_item_emite_evento_para_refrescar_comanda(self):
        pedido, item = self.crear_pedido_con_item()
        services.enviar_a_cocina(pedido=pedido, usuario=self.user)
        item.refresh_from_db()

        with patch('restaurante.services.emitir_evento_restaurante') as emitir:
            with self.captureOnCommitCallbacks(execute=True):
                services.actualizar_estado_item(
                    item=item,
                    nuevo_estado=PedidoItem.Estado.PREPARANDO,
                    usuario=self.user,
                )

        self.assertEqual(emitir.call_args.args[1], 'restaurante.item_estado_actualizado')
        payload = emitir.call_args.args[2]
        self.assertEqual(payload['pedido_id'], pedido.id)
        self.assertEqual(payload['item_id'], item.id)
        self.assertEqual(payload['estado'], PedidoItem.Estado.PREPARANDO)

    def test_dashboard_restaurante_renderiza(self):
        self.dar_permisos('operar_restaurante')
        self.client.force_login(self.user)

        response = self.client.get(reverse('restaurante_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Comandas abiertas')

    def test_comanda_renderiza(self):
        self.dar_permisos('operar_restaurante')
        pedido, _ = self.crear_pedido_con_item()
        self.client.force_login(self.user)

        response = self.client.get(reverse('restaurante_comanda', args=[pedido.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Detalle de comanda')
        self.assertContains(response, 'Propina')
        self.assertContains(response, 'Mixto')

    def test_kds_renderiza(self):
        self.dar_permisos('operar_kds')
        pedido, _ = self.crear_pedido_con_item()
        services.enviar_a_cocina(pedido=pedido, usuario=self.user)
        self.client.force_login(self.user)

        response = self.client.get(reverse('restaurante_kds'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Pendientes')
