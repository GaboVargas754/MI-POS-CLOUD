from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from configuraciones.utils import get_tienda_actual
from inventario.models import Categoria, MovimientoInventario, PrecioProducto, Producto
from ventas.models import DetalleVenta, PagoVenta, SesionCaja, Venta


class FlujoVentasTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='cajero', password='testpass')
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=[
            'operar_pos',
            'abrir_cerrar_caja',
            'cancelar_ventas',
            'ver_historial_ventas',
            'ver_estadisticas',
            'ver_turnos',
        ]))
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

    def crear_venta_con_detalle(self, estado='ACTIVA', total=Decimal('25.00'), cantidad=2):
        venta = Venta.objects.create(
            cajero=self.user,
            sesion=self.sesion,
            total=total,
            pago_recibido=total,
            cambio=Decimal('0.00'),
            metodo_pago='EFE',
            estado=estado,
        )
        DetalleVenta.objects.create(
            venta=venta,
            producto=self.producto,
            cantidad=cantidad,
            precio_unitario=Decimal('12.50'),
        )
        return venta

    def test_agregar_al_carrito_usa_precio_relacionado(self):
        response = self.client.post(reverse('agregar_al_carrito', args=[self.producto.id]))

        self.assertEqual(response.status_code, 200)
        carrito = self.client.session['carrito']
        self.assertEqual(carrito[str(self.producto.id)]['precio'], '12.50')
        self.assertEqual(carrito[str(self.producto.id)]['subtotal'], '12.50')
        self.assertContains(response, '$12.50')

    def test_agregar_por_codigo_agrega_producto_exacto(self):
        response = self.client.post(
            reverse('agregar_por_codigo'),
            {'codigo_barras': self.producto.codigo_barras},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Carrito-Resultado'], 'agregado')
        carrito = self.client.session['carrito']
        self.assertEqual(carrito[str(self.producto.id)]['cantidad'], 1)
        self.assertEqual(carrito[str(self.producto.id)]['precio'], '12.50')

    def test_agregar_por_codigo_normaliza_caracteres_de_control(self):
        response = self.client.post(
            reverse('agregar_por_codigo'),
            {'codigo_barras': '750000\r\n000001\t'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Carrito-Resultado'], 'agregado')
        carrito = self.client.session['carrito']
        self.assertEqual(carrito[str(self.producto.id)]['cantidad'], 1)

    def test_agregar_por_codigo_respeta_stock_disponible(self):
        self.producto.stock = 1
        self.producto.save(update_fields=['stock'])

        primera = self.client.post(reverse('agregar_por_codigo'), {'codigo_barras': self.producto.codigo_barras})
        segunda = self.client.post(reverse('agregar_por_codigo'), {'codigo_barras': self.producto.codigo_barras})

        self.assertEqual(primera['X-Carrito-Resultado'], 'agregado')
        self.assertEqual(segunda['X-Carrito-Resultado'], 'stock')
        carrito = self.client.session['carrito']
        self.assertEqual(carrito[str(self.producto.id)]['cantidad'], 1)
        self.assertContains(segunda, 'Stock insuficiente')

    def test_agregar_por_codigo_no_encontrado_no_modifica_carrito(self):
        response = self.client.post(reverse('agregar_por_codigo'), {'codigo_barras': 'NO-EXISTE'})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Carrito-Resultado'], 'no_encontrado')
        self.assertEqual(self.client.session.get('carrito'), {})

    def test_procesar_venta_asocia_sesion_y_descuenta_stock(self):
        self.client.post(reverse('agregar_al_carrito', args=[self.producto.id]))
        self.client.post(reverse('agregar_al_carrito', args=[self.producto.id]))

        response = self.client.post(reverse('procesar_venta'), {'pago_recibido': '30.00'})

        self.assertEqual(response.status_code, 200)
        venta = Venta.objects.get()
        self.assertEqual(venta.sesion, self.sesion)
        self.assertEqual(venta.tienda, get_tienda_actual(response.wsgi_request))
        self.assertEqual(venta.metodo_pago, 'EFE')
        self.assertEqual(venta.subtotal, Decimal('25.00'))
        self.assertEqual(venta.propina, Decimal('0.00'))
        self.assertEqual(venta.total, Decimal('25.00'))
        self.assertEqual(venta.pago_recibido, Decimal('30.00'))
        self.assertEqual(venta.cambio, Decimal('5.00'))
        self.assertEqual(list(venta.pagos.values_list('metodo_pago', 'monto')), [('EFE', Decimal('25.00'))])

        detalle = DetalleVenta.objects.get(venta=venta)
        self.assertEqual(detalle.precio_unitario, Decimal('12.50'))
        self.assertEqual(detalle.cantidad, 2)

        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 3)
        self.assertEqual(self.client.session.get('carrito'), {})

        movimiento = MovimientoInventario.objects.get(producto=self.producto, tipo=MovimientoInventario.Tipo.VENTA)
        self.assertEqual(movimiento.cantidad, -2)
        self.assertEqual(movimiento.stock_antes, 5)
        self.assertEqual(movimiento.stock_despues, 3)
        self.assertEqual(movimiento.venta, venta)
        self.assertEqual(movimiento.tienda, venta.tienda)
        self.assertEqual(movimiento.usuario, self.user)

    def test_procesar_venta_guarda_metodo_tarjeta_como_cobro_exacto(self):
        self.client.post(reverse('agregar_al_carrito', args=[self.producto.id]))

        response = self.client.post(reverse('procesar_venta'), {'metodo_pago': 'TAR'})

        self.assertEqual(response.status_code, 200)
        venta = Venta.objects.get()
        self.assertEqual(venta.metodo_pago, 'TAR')
        self.assertEqual(venta.total, Decimal('12.50'))
        self.assertEqual(venta.pago_recibido, Decimal('12.50'))
        self.assertEqual(venta.cambio, Decimal('0.00'))
        self.assertEqual(list(venta.pagos.values_list('metodo_pago', 'monto')), [('TAR', Decimal('12.50'))])
        self.assertContains(response, 'Tarjeta')

    def test_procesar_venta_guarda_pago_mixto(self):
        self.client.post(reverse('agregar_al_carrito', args=[self.producto.id]))
        self.client.post(reverse('agregar_al_carrito', args=[self.producto.id]))

        response = self.client.post(reverse('procesar_venta'), {
            'metodo_pago': 'MIX',
            'pago_efectivo': '10.00',
            'pago_tarjeta': '15.00',
            'pago_transferencia': '0',
        })

        self.assertEqual(response.status_code, 200)
        venta = Venta.objects.get()
        self.assertEqual(venta.metodo_pago, 'MIX')
        self.assertEqual(venta.total, Decimal('25.00'))
        self.assertEqual(venta.pago_recibido, Decimal('25.00'))
        self.assertEqual(venta.cambio, Decimal('0.00'))
        self.assertEqual(list(venta.pagos.values_list('metodo_pago', 'monto')), [
            ('EFE', Decimal('10.00')),
            ('TAR', Decimal('15.00')),
        ])

    def test_carrito_muestra_controles_de_cobro_rapido(self):
        response = self.client.post(reverse('agregar_al_carrito', args=[self.producto.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Método de pago')
        self.assertContains(response, 'Mixto')
        self.assertContains(response, 'pagos-mixtos')
        self.assertContains(response, 'pagos-rapidos')
        self.assertContains(response, 'setPagoRapido')
        self.assertContains(response, 'mostrarCobroRapido')
        self.assertContains(response, 'ocultarCobroRapido')
        self.assertContains(response, 'id="btn-mostrar-cobro"')
        self.assertContains(response, 'Confirmar')
        self.assertContains(response, 'actualizarMetodoPago')
        self.assertContains(response, 'hx-include="#controles-cobro"')

    def test_cerrar_caja_calcula_ventas_de_la_sesion(self):
        Venta.objects.create(
            cajero=self.user,
            sesion=self.sesion,
            total=Decimal('25.00'),
            pago_recibido=Decimal('30.00'),
            cambio=Decimal('5.00'),
        )
        Venta.objects.create(
            cajero=self.user,
            sesion=self.sesion,
            total=Decimal('99.00'),
            pago_recibido=Decimal('99.00'),
            cambio=Decimal('0.00'),
            estado='CANCELADA',
        )

        response = self.client.get(reverse('cerrar_caja'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['ventas_efectivo'], Decimal('25.00'))
        self.assertEqual(response.context['esperado_en_caja'], Decimal('75.00'))
        self.assertContains(response, 'diferencia_cierre')
        self.assertContains(response, 'calcularDiferenciaCierre')

    def test_cerrar_caja_rechaza_efectivo_negativo(self):
        response = self.client.post(reverse('cerrar_caja'), {'efectivo_cierre': '-1.00'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El efectivo de cierre no puede ser negativo')
        self.sesion.refresh_from_db()
        self.assertTrue(self.sesion.estado)

    def test_abrir_caja_muestra_navegacion_y_estilo_pos(self):
        self.sesion.delete()

        response = self.client.get(reverse('abrir_caja'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'POS')
        self.assertContains(response, 'border-green-600')
        self.assertContains(response, 'sm:hidden fixed bottom-0')
        self.assertContains(response, 'from-green-500')

    def test_abrir_caja_redirige_si_ya_hay_turno_abierto(self):
        response = self.client.get(reverse('abrir_caja'))

        self.assertRedirects(response, reverse('pantalla_pos'))

    def test_cerrar_caja_muestra_navegacion_y_estilo_pos(self):
        response = self.client.get(reverse('cerrar_caja'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'POS')
        self.assertContains(response, 'border-green-600')
        self.assertContains(response, 'sm:hidden fixed bottom-0')
        self.assertContains(response, 'from-green-500')

    def test_cerrar_caja_redirige_si_no_hay_turno_abierto(self):
        self.sesion.delete()

        response = self.client.get(reverse('cerrar_caja'))

        self.assertRedirects(response, reverse('abrir_caja'))

    def test_agregar_carrito_requiere_turno_abierto(self):
        self.sesion.delete()

        response = self.client.post(reverse('agregar_al_carrito', args=[self.producto.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['X-Carrito-Resultado'], 'sin_turno')
        self.assertContains(response, 'Abre caja antes de modificar el carrito')
        self.assertEqual(self.client.session.get('carrito'), {})

    def test_procesar_venta_requiere_turno_abierto(self):
        self.sesion.delete()
        session = self.client.session
        session['carrito'] = {
            str(self.producto.id): {
                'nombre': self.producto.nombre,
                'precio': '12.50',
                'cantidad': 1,
            }
        }
        session.save()

        response = self.client.post(reverse('procesar_venta'), {'pago_recibido': '20.00'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Abre caja antes de cobrar una venta')
        self.assertFalse(Venta.objects.exists())

    def test_procesar_venta_rechaza_producto_inactivo(self):
        self.producto.activo = False
        self.producto.save(update_fields=['activo'])
        session = self.client.session
        session['carrito'] = {
            str(self.producto.id): {
                'nombre': self.producto.nombre,
                'precio': '12.50',
                'cantidad': 1,
            }
        }
        session.save()

        response = self.client.post(reverse('procesar_venta'), {'pago_recibido': '20.00'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'está inactivo y no puede venderse')
        self.assertFalse(Venta.objects.exists())

    def test_pos_muestra_lector_nativo_con_enfoque(self):
        response = self.client.get(reverse('pantalla_pos'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'video-barras-pos')
        self.assertContains(response, 'BarcodeDetector')
        self.assertContains(response, 'enfocarCamaraPos')
        self.assertContains(response, 'btn-linterna-pos')
        self.assertContains(response, 'data-cart-total')
        self.assertContains(response, 'toast-carrito')
        self.assertContains(response, 'actualizarTotalCarritoMovil')
        self.assertContains(response, 'agregarCodigoEscaneado')
        self.assertContains(response, 'refrescarBusquedaActivaPos')
        self.assertContains(response, 'producto.precio_actualizado')
        self.assertContains(response, 'pos:notificacion')
        self.assertContains(response, reverse('agregar_por_codigo'))
        self.assertContains(response, 'aria-label="Cerrar turno"')
        self.assertNotContains(response, 'btn-pos-menu')
        self.assertNotContains(response, 'pos-mobile-menu')
        self.assertContains(response, 'sm:hidden fixed bottom-0')
        self.assertContains(response, 'bottom-20')
        self.assertContains(response, 'bottom-40')
        self.assertContains(response, reverse('cerrar_caja'))

    def test_pos_agrega_codigo_con_pistola_fisica(self):
        response = self.client.get(reverse('pantalla_pos'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'inicializarEscanerFisicoPos')
        self.assertContains(response, 'esEventoEnterEscanerFisico')
        self.assertContains(response, "event.code === 'NumpadEnter'")
        self.assertContains(response, 'event.keyCode === 13')
        self.assertContains(response, "event.inputType === 'insertLineBreak'")
        self.assertContains(response, 'normalizarCodigoEscaneado')
        self.assertContains(response, 'agregarCodigoEscaneado(codigo)')
        self.assertContains(response, 'limpiarBusquedaEscaneada')

    def test_pos_muestra_accesos_a_modulos_permitidos(self):
        self.user.user_permissions.add(
            Permission.objects.get(codename='ver_inventario'),
            Permission.objects.get(codename='gestionar_usuarios'),
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('pantalla_pos'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'pos-nav-link')
        self.assertContains(response, 'Estadísticas')
        self.assertContains(response, 'Inventario')
        self.assertContains(response, 'Sistema')
        self.assertContains(response, reverse('dashboard'))
        self.assertContains(response, reverse('inventario_dashboard'))
        self.assertContains(response, reverse('config_dashboard'))

    def test_dashboard_ventas_se_muestra_como_estadisticas(self):
        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'ESTADÍSTICAS')
        self.assertContains(response, 'Estadísticas de Ventas')
        self.assertContains(response, 'border-blue-600')
        self.assertContains(response, 'Histórico')
        self.assertContains(response, reverse('historial_ventas'))
        self.assertContains(response, 'Turnos')
        self.assertContains(response, reverse('historial_turnos'))
        self.assertContains(response, 'dashboard-estadisticas-tiempo-real')
        self.assertContains(response, reverse('dashboard_live'))
        self.assertContains(response, 'pos:notificacion')

    def test_dashboard_live_devuelve_partial_actualizable(self):
        self.crear_venta_con_detalle(total=Decimal('25.00'))

        response = self.client.get(reverse('dashboard_live'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_ventas'], Decimal('25.00'))
        self.assertContains(response, 'Ventas Totales')
        self.assertNotContains(response, 'Estadísticas de Ventas')

    def test_historial_ventas_muestra_tickets_y_resumen(self):
        venta = self.crear_venta_con_detalle()

        response = self.client.get(reverse('historial_ventas'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Histórico de Ventas')
        self.assertContains(response, f'Ticket #{venta.id}')
        self.assertContains(response, 'Agua')
        self.assertContains(response, '$25.00')
        self.assertContains(response, 'Efectivo')
        self.assertContains(response, reverse('imprimir_ticket', args=[venta.id]))

    def test_historial_ventas_resumen_excluye_canceladas(self):
        venta_activa = self.crear_venta_con_detalle(total=Decimal('25.00'))
        venta_cancelada = self.crear_venta_con_detalle(estado='CANCELADA', total=Decimal('99.00'))
        venta_cancelada.motivo_cancelacion = 'Cliente cancelo la compra'
        venta_cancelada.fecha_cancelacion = timezone.now()
        venta_cancelada.cancelado_por = self.user
        venta_cancelada.save(update_fields=['motivo_cancelacion', 'fecha_cancelacion', 'cancelado_por'])

        response = self.client.get(reverse('historial_ventas'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_vendido'], Decimal('25.00'))
        self.assertEqual(response.context['total_tickets'], 1)
        self.assertContains(response, f'Ticket #{venta_activa.id}')
        self.assertContains(response, f'Ticket #{venta_cancelada.id}')
        self.assertContains(response, 'Cancelada')
        self.assertContains(response, 'Cliente cancelo la compra')

    def test_historial_ventas_filtra_por_metodo_producto_y_fecha(self):
        categoria = self.producto.categoria
        jugo = Producto.objects.create(
            codigo_barras='750000000002',
            nombre='Jugo Natural',
            categoria=categoria,
            stock=4,
        )
        venta_agua = Venta.objects.create(
            cajero=self.user,
            sesion=self.sesion,
            total=Decimal('12.50'),
            pago_recibido=Decimal('12.50'),
            cambio=Decimal('0.00'),
            metodo_pago='EFE',
        )
        venta_jugo = Venta.objects.create(
            cajero=self.user,
            sesion=self.sesion,
            total=Decimal('15.00'),
            pago_recibido=Decimal('15.00'),
            cambio=Decimal('0.00'),
            metodo_pago='TAR',
        )
        DetalleVenta.objects.create(venta=venta_agua, producto=self.producto, cantidad=1, precio_unitario=Decimal('12.50'))
        DetalleVenta.objects.create(venta=venta_jugo, producto=jugo, cantidad=1, precio_unitario=Decimal('15.00'))

        response = self.client.get(reverse('historial_ventas'), {'metodo_pago': 'TAR'})

        self.assertContains(response, 'Jugo Natural')
        self.assertNotContains(response, 'Agua')

        response = self.client.get(reverse('historial_ventas'), {'q': 'Agua'})

        self.assertContains(response, 'Agua')
        self.assertNotContains(response, 'Jugo Natural')

        fecha = venta_jugo.fecha.date().isoformat()
        response = self.client.get(reverse('historial_ventas'), {'desde': fecha, 'hasta': fecha})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'historial-q')
        self.assertContains(response, 'Total del rango')

    def test_historial_turnos_muestra_resumen_y_corte(self):
        self.sesion.estado = False
        self.sesion.fecha_cierre = timezone.now()
        self.sesion.efectivo_cierre = Decimal('75.00')
        self.sesion.save(update_fields=['estado', 'fecha_cierre', 'efectivo_cierre'])
        venta = Venta.objects.create(
            cajero=self.user,
            sesion=self.sesion,
            total=Decimal('25.00'),
            pago_recibido=Decimal('25.00'),
            cambio=Decimal('0.00'),
            metodo_pago='EFE',
        )
        DetalleVenta.objects.create(venta=venta, producto=self.producto, cantidad=2, precio_unitario=Decimal('12.50'))

        response = self.client.get(reverse('historial_turnos'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Histórico de Turnos')
        self.assertContains(response, f'Turno #{self.sesion.id}')
        self.assertContains(response, 'Caja cuadrada')
        self.assertContains(response, '$25.00')
        self.assertContains(response, reverse('imprimir_corte', args=[self.sesion.id]))

    def test_historial_turnos_filtra_por_estado_y_cajero(self):
        otro_user = User.objects.create_user(username='otro', password='testpass')
        otro_turno = SesionCaja.objects.create(
            cajero=otro_user,
            fondo_inicial=Decimal('10.00'),
            estado=False,
            fecha_cierre=timezone.now(),
            efectivo_cierre=Decimal('10.00'),
        )

        response = self.client.get(reverse('historial_turnos'), {'estado': 'cerrada'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Turno #{otro_turno.id}')
        self.assertNotContains(response, f'Turno #{self.sesion.id}')

        response = self.client.get(reverse('historial_turnos'), {'cajero': otro_user.id})

        self.assertContains(response, 'otro')
        self.assertContains(response, f'Turno #{otro_turno.id}')
        self.assertNotContains(response, f'Turno #{self.sesion.id}')

    def test_imprimir_corte_muestra_totales_del_turno(self):
        self.sesion.estado = False
        self.sesion.fecha_cierre = timezone.now()
        self.sesion.efectivo_cierre = Decimal('80.00')
        self.sesion.save(update_fields=['estado', 'fecha_cierre', 'efectivo_cierre'])
        Venta.objects.create(
            cajero=self.user,
            sesion=self.sesion,
            total=Decimal('25.00'),
            pago_recibido=Decimal('25.00'),
            cambio=Decimal('0.00'),
            metodo_pago='EFE',
        )
        Venta.objects.create(
            cajero=self.user,
            sesion=self.sesion,
            total=Decimal('99.00'),
            pago_recibido=Decimal('99.00'),
            cambio=Decimal('0.00'),
            metodo_pago='EFE',
            estado='CANCELADA',
        )

        response = self.client.get(reverse('imprimir_corte', args=[self.sesion.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_ventas'], Decimal('25.00'))
        self.assertEqual(response.context['ventas_efectivo'], Decimal('25.00'))
        self.assertContains(response, 'Corte de Caja')
        self.assertContains(response, f'Turno #{self.sesion.id}')
        self.assertContains(response, '$25.00')
        self.assertContains(response, '$75.00')
        self.assertContains(response, '$5.00')

    def test_corte_suma_pago_mixto_por_metodo(self):
        self.sesion.estado = False
        self.sesion.fecha_cierre = timezone.now()
        self.sesion.efectivo_cierre = Decimal('70.00')
        self.sesion.save(update_fields=['estado', 'fecha_cierre', 'efectivo_cierre'])
        venta = Venta.objects.create(
            cajero=self.user,
            sesion=self.sesion,
            subtotal=Decimal('25.00'),
            total=Decimal('25.00'),
            pago_recibido=Decimal('25.00'),
            cambio=Decimal('0.00'),
            metodo_pago='MIX',
        )
        PagoVenta.objects.create(venta=venta, metodo_pago='EFE', monto=Decimal('10.00'))
        PagoVenta.objects.create(venta=venta, metodo_pago='TAR', monto=Decimal('15.00'))

        response = self.client.get(reverse('imprimir_corte', args=[self.sesion.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['ventas_efectivo'], Decimal('10.00'))
        self.assertEqual(response.context['ventas_tarjeta'], Decimal('15.00'))
        self.assertEqual(response.context['total_ventas'], Decimal('25.00'))
        self.assertEqual(response.context['esperado_en_caja'], Decimal('60.00'))

    def test_dashboard_excluye_ventas_canceladas(self):
        self.crear_venta_con_detalle(total=Decimal('25.00'))
        self.crear_venta_con_detalle(estado='CANCELADA', total=Decimal('99.00'))

        response = self.client.get(reverse('dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_ventas'], Decimal('25.00'))
        self.assertEqual(response.context['num_tickets'], 1)

    def test_cancelar_venta_get_muestra_detalle_y_motivo(self):
        venta = self.crear_venta_con_detalle()

        response = self.client.get(reverse('cancelar_venta', args=[venta.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Cancelar Ticket #{venta.id}')
        self.assertContains(response, 'Productos a reintegrar')
        self.assertContains(response, '+2 stock')
        self.assertContains(response, 'motivo_cancelacion')

    def test_cancelar_venta_requiere_permiso_granular(self):
        venta = self.crear_venta_con_detalle()
        supervisor = User.objects.create_user(username='supervisor', password='testpass')
        supervisor.user_permissions.add(Permission.objects.get(codename='ver_historial_ventas'))
        self.client.force_login(supervisor)

        response = self.client.get(reverse('cancelar_venta', args=[venta.id]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(reverse('portal_principal')))

    def test_cancelar_venta_rechaza_motivo_vacio(self):
        venta = self.crear_venta_con_detalle()
        self.producto.stock = 3
        self.producto.save(update_fields=['stock'])

        response = self.client.post(reverse('cancelar_venta', args=[venta.id]), {'motivo_cancelacion': '   '})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Captura el motivo de cancelación')
        venta.refresh_from_db()
        self.producto.refresh_from_db()
        self.assertEqual(venta.estado, 'ACTIVA')
        self.assertEqual(self.producto.stock, 3)

    def test_cancelar_venta_cambia_estado_y_reintegra_stock(self):
        venta = self.crear_venta_con_detalle()
        self.producto.stock = 3
        self.producto.save(update_fields=['stock'])

        response = self.client.post(
            reverse('cancelar_venta', args=[venta.id]),
            {'motivo_cancelacion': 'Error de cobro'},
        )

        self.assertRedirects(response, reverse('historial_ventas'))
        venta.refresh_from_db()
        self.producto.refresh_from_db()
        self.assertEqual(venta.estado, 'CANCELADA')
        self.assertEqual(venta.motivo_cancelacion, 'Error de cobro')
        self.assertEqual(venta.cancelado_por, self.user)
        self.assertIsNotNone(venta.fecha_cancelacion)
        self.assertEqual(self.producto.stock, 5)

        movimiento = MovimientoInventario.objects.get(producto=self.producto, tipo=MovimientoInventario.Tipo.CANCELACION)
        self.assertEqual(movimiento.cantidad, 2)
        self.assertEqual(movimiento.stock_antes, 3)
        self.assertEqual(movimiento.stock_despues, 5)
        self.assertEqual(movimiento.venta, venta)
        self.assertEqual(movimiento.usuario, self.user)
        self.assertEqual(movimiento.motivo, 'Error de cobro')

    def test_cancelar_venta_no_reintegra_dos_veces(self):
        venta = self.crear_venta_con_detalle(estado='CANCELADA')
        venta.motivo_cancelacion = 'Ya cancelado'
        venta.fecha_cancelacion = timezone.now()
        venta.cancelado_por = self.user
        venta.save(update_fields=['motivo_cancelacion', 'fecha_cancelacion', 'cancelado_por'])

        response = self.client.post(
            reverse('cancelar_venta', args=[venta.id]),
            {'motivo_cancelacion': 'Segundo intento'},
        )

        self.assertRedirects(response, reverse('historial_ventas'))
        self.producto.refresh_from_db()
        venta.refresh_from_db()
        self.assertEqual(self.producto.stock, 5)
        self.assertEqual(venta.motivo_cancelacion, 'Ya cancelado')
        self.assertFalse(MovimientoInventario.objects.filter(producto=self.producto).exists())

    def test_ticket_cancelado_muestra_estado_y_motivo(self):
        venta = self.crear_venta_con_detalle(estado='CANCELADA')
        venta.motivo_cancelacion = 'Ticket duplicado'
        venta.fecha_cancelacion = timezone.now()
        venta.cancelado_por = self.user
        venta.save(update_fields=['motivo_cancelacion', 'fecha_cancelacion', 'cancelado_por'])

        response = self.client.get(reverse('imprimir_ticket', args=[venta.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'TICKET CANCELADO')
        self.assertContains(response, 'Ticket duplicado')
        self.assertContains(response, f'Por: {self.user.username}')

    def test_busqueda_muestra_tarjetas_con_feedback_de_agregado(self):
        response = self.client.get(reverse('buscar_productos'), {'q': 'Agua'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'producto-resultado')
        self.assertContains(response, reverse('agregar_al_carrito', args=[self.producto.id]))

    def test_busqueda_no_muestra_productos_inactivos(self):
        self.producto.activo = False
        self.producto.save(update_fields=['activo'])

        response = self.client.get(reverse('buscar_productos'), {'q': 'Agua'})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'producto-resultado')
