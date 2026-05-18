from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from inventario.models import Categoria, HistorialPrecio, MovimientoInventario, PrecioProducto, Producto


class ProductoFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='inventario', password='testpass')
        self.user.user_permissions.add(*Permission.objects.filter(codename__in=[
            'ver_inventario',
            'editar_productos',
            'ajustar_stock',
            'editar_precios',
            'importar_exportar_inventario',
            'imprimir_etiquetas',
        ]))
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
        self.assertContains(response, 'Precio de venta')

    def test_formulario_producto_crea_producto_precio_y_movimiento_inicial(self):
        categoria = Categoria.objects.create(nombre='Bebidas')

        response = self.client.post(reverse('nuevo_producto'), {
            'codigo_barras': '750000000100',
            'nombre': 'Agua Premium',
            'categoria': categoria.id,
            'stock': '7',
            'stock_minimo': '2',
            'costo': '5.00',
            'precio': '12.50',
        })

        self.assertRedirects(response, reverse('lista_inventario'))
        producto = Producto.objects.get(codigo_barras='750000000100')
        self.assertEqual(producto.nombre, 'Agua Premium')
        self.assertEqual(producto.stock, 7)
        self.assertEqual(producto.stock_minimo, 2)
        self.assertEqual(producto.precios.costo, Decimal('5.00'))
        self.assertEqual(producto.precios.precio, Decimal('12.50'))

        movimiento = MovimientoInventario.objects.get(producto=producto)
        self.assertEqual(movimiento.tipo, MovimientoInventario.Tipo.ENTRADA)
        self.assertEqual(movimiento.cantidad, 7)
        self.assertEqual(movimiento.stock_antes, 0)
        self.assertEqual(movimiento.stock_despues, 7)

        historial = HistorialPrecio.objects.get(producto=producto)
        self.assertIsNone(historial.precio_anterior)
        self.assertEqual(historial.precio_nuevo, Decimal('12.50'))

    def test_formulario_producto_actualiza_precio_existente(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        producto = Producto.objects.create(codigo_barras='750000000101', nombre='Té', categoria=categoria, stock=4, stock_minimo=2)
        precio = PrecioProducto.objects.create(producto=producto, costo=Decimal('3.00'), precio=Decimal('8.00'))

        response = self.client.post(reverse('editar_producto', args=[producto.id]), {
            'codigo_barras': producto.codigo_barras,
            'nombre': producto.nombre,
            'categoria': categoria.id,
            'stock': '4',
            'stock_minimo': '2',
            'costo': '4.00',
            'precio': '9.50',
        })

        self.assertRedirects(response, reverse('lista_inventario'))
        precio.refresh_from_db()
        self.assertEqual(precio.costo, Decimal('4.00'))
        self.assertEqual(precio.precio, Decimal('9.50'))
        historial = HistorialPrecio.objects.get(producto=producto)
        self.assertEqual(historial.costo_anterior, Decimal('3.00'))
        self.assertEqual(historial.costo_nuevo, Decimal('4.00'))
        self.assertEqual(historial.precio_anterior, Decimal('8.00'))
        self.assertEqual(historial.precio_nuevo, Decimal('9.50'))

    def test_lista_productos_incluye_tarjetas_moviles(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        producto = Producto.objects.create(
            codigo_barras='750000000001',
            nombre='Agua Mineral',
            categoria=categoria,
            stock=8,
        )
        PrecioProducto.objects.create(producto=producto, costo=Decimal('5.00'), precio=Decimal('12.50'))

        response = self.client.get(reverse('lista_inventario'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'INVENTARIO')
        self.assertContains(response, 'border-purple-600')
        self.assertContains(response, 'md:hidden divide-y')
        self.assertContains(response, 'Agua Mineral')
        self.assertContains(response, 'filtros-inventario-form')
        self.assertContains(response, 'abrirEscanerFiltroInventario')
        self.assertContains(response, 'abrirProductoPorCodigoInventario')
        self.assertContains(response, reverse('resolver_codigo_producto'))
        self.assertContains(response, 'BarcodeDetector')
        self.assertContains(response, reverse('ajustar_stock', args=[producto.id]))
        self.assertContains(response, reverse('movimientos_producto', args=[producto.id]))
        self.assertContains(response, reverse('historial_precios_producto', args=[producto.id]))
        self.assertContains(response, reverse('entrada_rapida'))
        self.assertContains(response, reverse('importar_productos_csv'))
        self.assertContains(response, reverse('exportar_productos_csv'))
        self.assertContains(response, reverse('imprimir_etiquetas'))
        self.assertContains(response, 'inventario-lista-tiempo-real')
        self.assertContains(response, reverse('lista_inventario_live'))
        self.assertContains(response, 'pos:notificacion')

    def test_lista_inventario_live_devuelve_resultados_filtrados(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        agua = Producto.objects.create(codigo_barras='750000000001', nombre='Agua Mineral', categoria=categoria, stock=8)
        pan = Producto.objects.create(codigo_barras='750000000002', nombre='Pan Dulce', categoria=categoria, stock=4)
        PrecioProducto.objects.create(producto=agua, costo=Decimal('5.00'), precio=Decimal('12.50'))
        PrecioProducto.objects.create(producto=pan, costo=Decimal('4.00'), precio=Decimal('10.00'))

        response = self.client.get(
            reverse('lista_inventario_live'),
            {'q': 'Agua'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Agua Mineral')
        self.assertNotContains(response, 'Pan Dulce')
        self.assertNotContains(response, 'Catálogo de Productos')

    def test_resolver_codigo_producto_existente_abre_edicion(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        producto = Producto.objects.create(
            codigo_barras='750000000001',
            nombre='Agua Mineral',
            categoria=categoria,
            stock=8,
        )

        response = self.client.get(reverse('resolver_codigo_producto'), {'codigo_barras': producto.codigo_barras})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Código encontrado')
        self.assertContains(response, 'Editar Producto')
        self.assertContains(response, producto.nombre)
        self.assertContains(response, reverse('editar_producto', args=[producto.id]))

    def test_resolver_codigo_producto_nuevo_precarga_codigo(self):
        response = self.client.get(reverse('resolver_codigo_producto'), {'codigo_barras': '750000000099'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Código nuevo')
        self.assertContains(response, 'Nuevo Producto')
        self.assertContains(response, 'value="750000000099"')
        self.assertContains(response, reverse('nuevo_producto'))

    def test_lista_productos_filtra_por_busqueda_categoria_y_stock(self):
        bebidas = Categoria.objects.create(nombre='Bebidas')
        panaderia = Categoria.objects.create(nombre='Panadería')
        agua = Producto.objects.create(codigo_barras='750000000001', nombre='Agua Mineral', categoria=bebidas, stock=8)
        pan = Producto.objects.create(codigo_barras='750000000002', nombre='Pan Dulce', categoria=panaderia, stock=0)
        PrecioProducto.objects.create(producto=agua, costo=Decimal('5.00'), precio=Decimal('12.50'))
        PrecioProducto.objects.create(producto=pan, costo=Decimal('4.00'), precio=Decimal('10.00'))

        response = self.client.get(reverse('lista_inventario'), {'q': 'Agua'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Agua Mineral')
        self.assertNotContains(response, 'Pan Dulce')

        response = self.client.get(reverse('lista_inventario'), {'categoria': panaderia.id})

        self.assertContains(response, 'Pan Dulce')
        self.assertNotContains(response, 'Agua Mineral')

        response = self.client.get(reverse('lista_inventario'), {'stock': 'agotado'})

        self.assertContains(response, 'Pan Dulce')
        self.assertNotContains(response, 'Agua Mineral')

    def test_lista_productos_filtra_bajo_stock_por_minimo_configurable(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        suficiente = Producto.objects.create(codigo_barras='750000000010', nombre='Agua Grande', categoria=categoria, stock=4, stock_minimo=2)
        bajo = Producto.objects.create(codigo_barras='750000000011', nombre='Agua Chica', categoria=categoria, stock=3, stock_minimo=3)
        PrecioProducto.objects.create(producto=suficiente, costo=Decimal('5.00'), precio=Decimal('12.50'))
        PrecioProducto.objects.create(producto=bajo, costo=Decimal('4.00'), precio=Decimal('10.00'))

        response = self.client.get(reverse('lista_inventario'), {'stock': 'bajo'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Agua Chica')
        self.assertNotContains(response, 'Agua Grande')

    def test_lista_productos_oculta_inactivos_por_default_y_filtra_estado(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        activo = Producto.objects.create(codigo_barras='750000000012', nombre='Producto vigente', categoria=categoria, stock=4)
        inactivo = Producto.objects.create(codigo_barras='750000000013', nombre='Fuera de venta', categoria=categoria, stock=4, activo=False)

        response = self.client.get(reverse('lista_inventario'))

        self.assertContains(response, activo.nombre)
        self.assertNotContains(response, inactivo.nombre)

        response = self.client.get(reverse('lista_inventario'), {'estado': 'inactivos'})

        self.assertContains(response, inactivo.nombre)
        self.assertNotContains(response, activo.nombre)

    def test_ajustar_stock_cambia_stock_y_registra_movimiento(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        producto = Producto.objects.create(codigo_barras='750000000020', nombre='Refresco', categoria=categoria, stock=8)

        response = self.client.get(reverse('ajustar_stock', args=[producto.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ajuste de inventario')
        self.assertContains(response, 'Stock actual')

        response = self.client.post(reverse('ajustar_stock', args=[producto.id]), {
            'nuevo_stock': '11',
            'motivo': 'Entrada de proveedor',
        })

        self.assertRedirects(response, reverse('lista_inventario'))
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 11)

        movimiento = MovimientoInventario.objects.get(producto=producto)
        self.assertEqual(movimiento.tipo, MovimientoInventario.Tipo.AJUSTE)
        self.assertEqual(movimiento.cantidad, 3)
        self.assertEqual(movimiento.stock_antes, 8)
        self.assertEqual(movimiento.stock_despues, 11)
        self.assertEqual(movimiento.usuario, self.user)
        self.assertEqual(movimiento.motivo, 'Entrada de proveedor')

    def test_ajustar_stock_requiere_permiso_granular(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        producto = Producto.objects.create(codigo_barras='750000000024', nombre='Refresco', categoria=categoria, stock=8)
        viewer = User.objects.create_user(username='viewer', password='testpass')
        viewer.user_permissions.add(Permission.objects.get(codename='ver_inventario'))
        self.client.force_login(viewer)

        response = self.client.get(reverse('ajustar_stock', args=[producto.id]))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(reverse('portal_principal')))

    def test_ajustar_stock_requiere_motivo(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        producto = Producto.objects.create(codigo_barras='750000000021', nombre='Jugo', categoria=categoria, stock=8)

        response = self.client.post(reverse('ajustar_stock', args=[producto.id]), {
            'nuevo_stock': '10',
            'motivo': '',
        })

        self.assertEqual(response.status_code, 200)
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 8)
        self.assertFalse(MovimientoInventario.objects.filter(producto=producto).exists())

    def test_movimientos_producto_muestra_kardex(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        producto = Producto.objects.create(codigo_barras='750000000022', nombre='Leche', categoria=categoria, stock=6)
        MovimientoInventario.objects.create(
            producto=producto,
            tipo=MovimientoInventario.Tipo.AJUSTE,
            cantidad=2,
            stock_antes=4,
            stock_despues=6,
            usuario=self.user,
            motivo='Conteo físico',
        )

        response = self.client.get(reverse('movimientos_producto', args=[producto.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Kardex de producto')
        self.assertContains(response, 'Leche')
        self.assertContains(response, 'Conteo físico')

    def test_historial_precios_producto_muestra_cambios(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        producto = Producto.objects.create(codigo_barras='750000000023', nombre='Té Verde', categoria=categoria, stock=6)
        HistorialPrecio.objects.create(
            producto=producto,
            costo_anterior=Decimal('3.00'),
            costo_nuevo=Decimal('4.00'),
            precio_anterior=Decimal('8.00'),
            precio_nuevo=Decimal('9.00'),
            usuario=self.user,
            motivo='Cambio de proveedor',
        )

        response = self.client.get(reverse('historial_precios_producto', args=[producto.id]))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Historial de precios')
        self.assertContains(response, 'Cambio de proveedor')
        self.assertContains(response, '$9.00')

    def test_dashboard_inventario_muestra_alertas_y_movimientos(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        agotado = Producto.objects.create(codigo_barras='750000000030', nombre='Agotado', categoria=categoria, stock=0)
        bajo = Producto.objects.create(codigo_barras='750000000031', nombre='Bajo Stock', categoria=categoria, stock=2, stock_minimo=3)
        ok = Producto.objects.create(codigo_barras='750000000032', nombre='Stock OK', categoria=categoria, stock=4, stock_minimo=1)
        PrecioProducto.objects.create(producto=bajo, costo=Decimal('2.00'), precio=Decimal('5.00'))
        PrecioProducto.objects.create(producto=ok, costo=Decimal('3.00'), precio=Decimal('10.00'))
        Producto.objects.create(codigo_barras='750000000033', nombre='Inactivo', categoria=categoria, stock=10, activo=False)
        MovimientoInventario.objects.create(
            producto=bajo,
            tipo=MovimientoInventario.Tipo.AJUSTE,
            cantidad=-1,
            stock_antes=3,
            stock_despues=2,
            usuario=self.user,
            motivo='Merma',
        )

        response = self.client.get(reverse('inventario_dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_productos'], 3)
        self.assertEqual(response.context['agotados'], 1)
        self.assertEqual(response.context['bajo_stock'], 1)
        self.assertEqual(response.context['sin_precio'], 1)
        self.assertEqual(response.context['inactivos'], 1)
        self.assertContains(response, 'Productos que requieren atención')
        self.assertContains(response, 'Movimientos recientes')
        self.assertContains(response, 'Entrada Rápida')
        self.assertContains(response, agotado.nombre)
        self.assertContains(response, bajo.nombre)
        self.assertContains(response, 'inventario-dashboard-tiempo-real')
        self.assertContains(response, reverse('inventario_dashboard_live'))
        self.assertContains(response, 'pos:notificacion')

    def test_dashboard_inventario_live_devuelve_partial_actualizable(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        Producto.objects.create(codigo_barras='750000000030', nombre='Agotado', categoria=categoria, stock=0)

        response = self.client.get(reverse('inventario_dashboard_live'), HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['agotados'], 1)
        self.assertContains(response, 'Productos que requieren atención')
        self.assertNotContains(response, 'Control de productos')

    def test_movimiento_inventario_emite_eventos_realtime(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        producto = Producto.objects.create(codigo_barras='750000000034', nombre='Agua Chica', categoria=categoria, stock=6, stock_minimo=5)

        with patch('core.notifications.emitir_notificacion_todas_tiendas') as emitir:
            with self.captureOnCommitCallbacks(execute=True):
                MovimientoInventario.registrar(
                    producto=producto,
                    tipo=MovimientoInventario.Tipo.AJUSTE,
                    cantidad=-2,
                    stock_antes=6,
                    stock_despues=4,
                    usuario=self.user,
                    motivo='Merma',
                )

        eventos = [call.args[0] for call in emitir.call_args_list]
        self.assertIn('inventario.movimiento', eventos)
        self.assertIn('inventario.stock_bajo', eventos)
        payload_bajo = emitir.call_args_list[1].args[1]
        self.assertEqual(payload_bajo['producto'], producto.nombre)
        self.assertEqual(payload_bajo['stock'], 4)
        self.assertEqual(payload_bajo['nivel'], 'warning')

    def test_actualizar_precio_inline_usa_decimal_y_rechaza_negativos(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        producto = Producto.objects.create(codigo_barras='750000000040', nombre='Café', categoria=categoria, stock=5)
        precio = PrecioProducto.objects.create(producto=producto, costo=Decimal('5.00'), precio=Decimal('12.50'))

        response = self.client.post(reverse('actualizar_precio_inline', args=[producto.id]), {'precio': '13.75'})

        self.assertEqual(response.status_code, 200)
        precio.refresh_from_db()
        self.assertEqual(precio.precio, Decimal('13.75'))
        self.assertTrue(HistorialPrecio.objects.filter(producto=producto, precio_nuevo=Decimal('13.75')).exists())

        response = self.client.post(reverse('actualizar_precio_inline', args=[producto.id]), {'precio': '-1'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'El precio no puede ser negativo')
        precio.refresh_from_db()
        self.assertEqual(precio.precio, Decimal('13.75'))

    def test_actualizar_precio_inline_emite_evento_realtime(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        producto = Producto.objects.create(codigo_barras='750000000042', nombre='Café Realtime', categoria=categoria, stock=5)
        PrecioProducto.objects.create(producto=producto, costo=Decimal('5.00'), precio=Decimal('12.50'))

        with patch('core.notifications.emitir_producto_actualizado') as emitir:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(reverse('actualizar_precio_inline', args=[producto.id]), {'precio': '13.75'})

        self.assertEqual(response.status_code, 200)
        emitir.assert_called_once()
        self.assertEqual(emitir.call_args.args[1], 'producto.precio_actualizado')
        self.assertEqual(emitir.call_args.args[2]['precio'], '13.75')

    def test_actualizar_precio_inline_requiere_permiso_granular(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        producto = Producto.objects.create(codigo_barras='750000000041', nombre='Café', categoria=categoria, stock=5)
        precio = PrecioProducto.objects.create(producto=producto, costo=Decimal('5.00'), precio=Decimal('12.50'))
        editor = User.objects.create_user(username='editor', password='testpass')
        editor.user_permissions.add(Permission.objects.get(codename='editar_productos'))
        self.client.force_login(editor)

        response = self.client.post(reverse('actualizar_precio_inline', args=[producto.id]), {'precio': '13.75'})

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith(reverse('portal_principal')))
        precio.refresh_from_db()
        self.assertEqual(precio.precio, Decimal('12.50'))
        self.assertFalse(HistorialPrecio.objects.filter(producto=producto).exists())

    def test_entrada_rapida_registra_stock_y_movimiento(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        producto = Producto.objects.create(codigo_barras='750000000050', nombre='Soda', categoria=categoria, stock=5)

        response = self.client.get(reverse('entrada_rapida'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Entrada rápida')
        self.assertContains(response, 'abrirCamaraEntrada')
        self.assertContains(response, 'BarcodeDetector')

        response = self.client.post(reverse('entrada_rapida'), {
            'codigo_barras': producto.codigo_barras,
            'cantidad': '4',
            'motivo': 'Proveedor',
        })

        self.assertRedirects(response, reverse('entrada_rapida'))
        producto.refresh_from_db()
        self.assertEqual(producto.stock, 9)
        movimiento = MovimientoInventario.objects.get(producto=producto)
        self.assertEqual(movimiento.tipo, MovimientoInventario.Tipo.ENTRADA)
        self.assertEqual(movimiento.cantidad, 4)
        self.assertEqual(movimiento.stock_antes, 5)
        self.assertEqual(movimiento.stock_despues, 9)

    def test_exportar_productos_csv_respeta_filtros(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        activo = Producto.objects.create(codigo_barras='750000000060', nombre='Activo CSV', categoria=categoria, stock=5)
        inactivo = Producto.objects.create(codigo_barras='750000000061', nombre='Inactivo CSV', categoria=categoria, stock=5, activo=False)
        PrecioProducto.objects.create(producto=activo, costo=Decimal('3.00'), precio=Decimal('8.00'))

        response = self.client.get(reverse('exportar_productos_csv'))

        self.assertEqual(response.status_code, 200)
        contenido = response.content.decode('utf-8-sig')
        self.assertIn('codigo_barras,nombre,categoria,stock,stock_minimo,costo,precio,activo', contenido)
        self.assertIn('Activo CSV', contenido)
        self.assertNotIn('Inactivo CSV', contenido)

        response = self.client.get(reverse('exportar_productos_csv'), {'estado': 'inactivos'})
        contenido = response.content.decode('utf-8-sig')
        self.assertIn(inactivo.nombre, contenido)

    def test_importar_productos_csv_crea_actualiza_y_registra_historial(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        existente = Producto.objects.create(codigo_barras='750000000070', nombre='Viejo', categoria=categoria, stock=2)
        PrecioProducto.objects.create(producto=existente, costo=Decimal('1.00'), precio=Decimal('2.00'))
        contenido = (
            'codigo_barras,nombre,categoria,stock,stock_minimo,costo,precio,activo\n'
            '750000000070,Nuevo Nombre,Bebidas,5,2,2.00,4.00,1\n'
            '750000000071,Nuevo Producto,Dulces,3,1,1.50,3.50,0\n'
        ).encode('utf-8')
        archivo = SimpleUploadedFile('productos.csv', contenido, content_type='text/csv')

        response = self.client.post(reverse('importar_productos_csv'), {'archivo': archivo})

        self.assertEqual(response.status_code, 200)
        existente.refresh_from_db()
        nuevo = Producto.objects.get(codigo_barras='750000000071')
        self.assertEqual(existente.nombre, 'Nuevo Nombre')
        self.assertEqual(existente.stock, 5)
        self.assertFalse(nuevo.activo)
        self.assertEqual(nuevo.precios.precio, Decimal('3.50'))
        self.assertEqual(MovimientoInventario.objects.filter(producto=existente).count(), 1)
        self.assertEqual(HistorialPrecio.objects.filter(producto=existente, precio_nuevo=Decimal('4.00')).count(), 1)
        self.assertContains(response, 'Creados')

    def test_imprimir_etiquetas_muestra_codigo_y_jsbarcode(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        producto = Producto.objects.create(codigo_barras='750000000080', nombre='Etiqueta Producto', categoria=categoria, stock=5)
        PrecioProducto.objects.create(producto=producto, costo=Decimal('3.00'), precio=Decimal('8.00'))

        response = self.client.get(reverse('imprimir_etiquetas'), {'ids': str(producto.id)})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Etiqueta Producto')
        self.assertContains(response, 'JsBarcode')
        self.assertContains(response, producto.codigo_barras)

    def test_lista_categorias_filtra_por_texto(self):
        Categoria.objects.create(nombre='Bebidas', descripcion='Botellas y latas')
        Categoria.objects.create(nombre='Limpieza', descripcion='Hogar')

        response = self.client.get(reverse('lista_categorias'), {'q': 'Bebidas'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'filtro-categorias-q')
        self.assertContains(response, 'Bebidas')
        self.assertNotContains(response, 'Limpieza')

    def test_lista_precios_filtra_por_producto(self):
        categoria = Categoria.objects.create(nombre='Bebidas')
        agua = Producto.objects.create(codigo_barras='750000000001', nombre='Agua Mineral', categoria=categoria, stock=8)
        jugo = Producto.objects.create(codigo_barras='750000000003', nombre='Jugo Natural', categoria=categoria, stock=4)
        PrecioProducto.objects.create(producto=agua, costo=Decimal('5.00'), precio=Decimal('12.50'))
        PrecioProducto.objects.create(producto=jugo, costo=Decimal('6.00'), precio=Decimal('15.00'))

        response = self.client.get(reverse('lista_precios'), {'q': 'Jugo'})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'filtro-precios-q')
        self.assertContains(response, 'Jugo Natural')
        self.assertNotContains(response, 'Agua Mineral')
