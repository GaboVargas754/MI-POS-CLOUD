from decimal import Decimal

from django.contrib.auth.models import Permission, User
from django.test import TestCase
from django.urls import reverse
from inventario.models import Categoria, PrecioProducto, Producto


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
        self.assertContains(response, 'BarcodeDetector')

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
