import csv
from decimal import Decimal, InvalidOperation
from io import TextIOWrapper

from django.contrib import messages
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.db.models import F, Q
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from inventario.models import Categoria, HistorialPrecio, MovimientoInventario, PrecioProducto, Producto
from inventario.forms import AjusteStockForm, EntradaRapidaForm, ImportarProductosForm, ProductoForm
from configuraciones.utils import get_tienda_actual
from core.utils import get_config_context, get_querystring_without_page


def _str_to_bool(value):
    return str(value).strip().lower() not in {'0', 'false', 'no', 'inactivo', 'inactive'}


def _decimal_csv(value, default=None):
    value = str(value or '').strip()
    if not value:
        return default
    return Decimal(value)


def _int_csv(value, default=0):
    value = str(value or '').strip()
    if not value:
        return default
    return int(value)


def _precio_actual(producto):
    try:
        return producto.precios
    except PrecioProducto.DoesNotExist:
        return None


def _guardar_precio_producto(producto, costo, precio, usuario, motivo, tienda=None):
    if precio is None:
        return None

    costo = costo if costo is not None else Decimal('0.00')
    precio_actual = _precio_actual(producto)
    costo_anterior = precio_actual.costo if precio_actual else None
    precio_anterior = precio_actual.precio if precio_actual else None

    if precio_actual and costo_anterior == costo and precio_anterior == precio:
        return precio_actual

    precio_obj, _ = PrecioProducto.objects.update_or_create(
        producto=producto,
        defaults={'costo': costo, 'precio': precio},
    )
    HistorialPrecio.objects.create(
        producto=producto,
        tienda=tienda,
        costo_anterior=costo_anterior,
        costo_nuevo=costo,
        precio_anterior=precio_anterior,
        precio_nuevo=precio,
        usuario=usuario,
        motivo=motivo,
    )
    return precio_obj


def _productos_filtrados(request):
    query = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '').strip()
    stock = request.GET.get('stock', '').strip()
    estado = request.GET.get('estado', 'activos').strip() or 'activos'
    productos_list = Producto.objects.select_related('categoria', 'precios').all().order_by('nombre')

    if estado == 'inactivos':
        productos_list = productos_list.filter(activo=False)
    elif estado != 'todos':
        estado = 'activos'
        productos_list = productos_list.filter(activo=True)

    if query:
        productos_list = productos_list.filter(
            Q(nombre__icontains=query)
            | Q(codigo_barras__icontains=query)
            | Q(categoria__nombre__icontains=query)
        )

    if categoria_id:
        productos_list = productos_list.filter(categoria_id=categoria_id)

    if stock == 'con_stock':
        productos_list = productos_list.filter(stock__gt=0)
    elif stock == 'bajo':
        productos_list = productos_list.filter(stock__gt=0, stock__lte=F('stock_minimo'))
    elif stock == 'agotado':
        productos_list = productos_list.filter(stock__lte=0)
    elif stock == 'sin_precio':
        productos_list = productos_list.filter(precios__isnull=True)

    return productos_list, {
        'query': query,
        'categoria_id': categoria_id,
        'stock': stock,
        'estado': estado,
    }

@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
def lista_inventario(request):
    productos_list, filtros = _productos_filtrados(request)

    per_page = request.GET.get('per_page', 10)

    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 10

    paginator = Paginator(productos_list, per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'inventario/productos/lista.html', {
        **get_config_context('Inventario', 'border-purple-600'),
        'page_obj': page_obj,
        'per_page': per_page,
        **filtros,
        'categorias': Categoria.objects.all().order_by('nombre'),
        'querystring': get_querystring_without_page(request),
    })

@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
def editar_producto(request, pk=None):
    tienda_actual = get_tienda_actual(request)
    if pk:
        producto = get_object_or_404(Producto, pk=pk)
        titulo = "Editar Producto"
    else:
        producto = None
        titulo = "Nuevo Producto"

    if request.method == 'POST':
        stock_antes = producto.stock if producto else 0
        form = ProductoForm(request.POST, instance=producto)
        if form.is_valid():
            with transaction.atomic():
                if producto:
                    Producto.objects.select_for_update().get(pk=producto.pk)

                producto_guardado = form.save()
                _guardar_precio_producto(
                    producto_guardado,
                    form.cleaned_data.get('costo'),
                    form.cleaned_data.get('precio'),
                    request.user,
                    'Edición de producto',
                    tienda_actual,
                )

                if producto is None and producto_guardado.stock > 0:
                    MovimientoInventario.registrar(
                        producto=producto_guardado,
                        tipo=MovimientoInventario.Tipo.ENTRADA,
                        cantidad=producto_guardado.stock,
                        stock_antes=0,
                        stock_despues=producto_guardado.stock,
                        usuario=request.user,
                        tienda=tienda_actual,
                        motivo='Stock inicial al crear producto.',
                    )
                elif producto is not None and stock_antes != producto_guardado.stock:
                    MovimientoInventario.registrar(
                        producto=producto_guardado,
                        tipo=MovimientoInventario.Tipo.AJUSTE,
                        cantidad=producto_guardado.stock - stock_antes,
                        stock_antes=stock_antes,
                        stock_despues=producto_guardado.stock,
                        usuario=request.user,
                        tienda=tienda_actual,
                        motivo='Ajuste desde edición de producto.',
                    )
            return redirect('lista_inventario')
    else:
        initial = {}
        if producto is None:
            initial['codigo_barras'] = request.GET.get('codigo_barras', '').strip()
        form = ProductoForm(instance=producto, initial=initial)

    return render(request, 'inventario/productos/formulario.html', {
        'form': form,
        'producto': producto,
        'titulo': titulo,
        'is_instance': producto is not None
    })


@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
def resolver_codigo_producto(request):
    codigo_barras = request.GET.get('codigo_barras', '').strip()
    producto = Producto.objects.filter(codigo_barras=codigo_barras).first()

    if producto:
        return render(request, 'inventario/productos/formulario.html', {
            'form': ProductoForm(instance=producto),
            'producto': producto,
            'titulo': 'Editar Producto',
            'is_instance': True,
            'form_action': reverse('editar_producto', args=[producto.id]),
            'codigo_resuelto': codigo_barras,
            'producto_encontrado': True,
        })

    return render(request, 'inventario/productos/formulario.html', {
        'form': ProductoForm(initial={'codigo_barras': codigo_barras}),
        'producto': None,
        'titulo': 'Nuevo Producto',
        'is_instance': False,
        'form_action': reverse('nuevo_producto'),
        'codigo_resuelto': codigo_barras,
        'producto_encontrado': False,
    })


@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
@require_http_methods(["GET", "POST"])
def ajustar_stock(request, pk):
    tienda_actual = get_tienda_actual(request)
    producto = get_object_or_404(Producto.objects.select_related('categoria'), pk=pk)

    if request.method == 'POST':
        form = AjusteStockForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                producto = Producto.objects.select_for_update().get(pk=pk)
                stock_antes = producto.stock
                nuevo_stock = form.cleaned_data['nuevo_stock']

                if nuevo_stock == stock_antes:
                    form.add_error('nuevo_stock', 'El stock nuevo es igual al stock actual.')
                else:
                    producto.stock = nuevo_stock
                    producto.full_clean()
                    producto.save(update_fields=['stock'])
                    MovimientoInventario.registrar(
                        producto=producto,
                        tipo=MovimientoInventario.Tipo.AJUSTE,
                        cantidad=nuevo_stock - stock_antes,
                        stock_antes=stock_antes,
                        stock_despues=nuevo_stock,
                        usuario=request.user,
                        tienda=tienda_actual,
                        motivo=form.cleaned_data['motivo'].strip(),
                    )
                    return redirect('lista_inventario')
    else:
        form = AjusteStockForm(initial={'nuevo_stock': producto.stock})

    return render(request, 'inventario/productos/ajustar_stock.html', {
        'form': form,
        'producto': producto,
    })


@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
def movimientos_producto(request, pk):
    producto = get_object_or_404(Producto.objects.select_related('categoria', 'precios'), pk=pk)
    tienda_actual = get_tienda_actual(request)
    movimientos = producto.movimientos.select_related('usuario', 'venta', 'tienda').filter(Q(tienda=tienda_actual) | Q(tienda__isnull=True))

    per_page = request.GET.get('per_page', 20)
    try:
        per_page = int(per_page)
    except ValueError:
        per_page = 20

    paginator = Paginator(movimientos, per_page)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'inventario/productos/movimientos.html', {
        **get_config_context('Inventario', 'border-purple-600'),
        'producto': producto,
        'page_obj': page_obj,
        'per_page': per_page,
        'querystring': get_querystring_without_page(request),
    })


@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
def historial_precios_producto(request, pk):
    producto = get_object_or_404(Producto.objects.select_related('categoria', 'precios'), pk=pk)
    tienda_actual = get_tienda_actual(request)
    historial = producto.historial_precios.select_related('usuario', 'tienda').filter(Q(tienda=tienda_actual) | Q(tienda__isnull=True))
    paginator = Paginator(historial, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'inventario/productos/historial_precios.html', {
        **get_config_context('Inventario', 'border-purple-600'),
        'producto': producto,
        'page_obj': page_obj,
        'querystring': get_querystring_without_page(request),
    })


@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
@require_http_methods(["GET", "POST"])
def entrada_rapida(request):
    tienda_actual = get_tienda_actual(request)
    if request.method == 'POST':
        form = EntradaRapidaForm(request.POST)
        if form.is_valid():
            codigo = form.cleaned_data['codigo_barras']
            cantidad = form.cleaned_data['cantidad']
            motivo = form.cleaned_data['motivo']

            with transaction.atomic():
                producto = Producto.objects.select_for_update().filter(codigo_barras=codigo).first()
                if not producto:
                    form.add_error('codigo_barras', 'No existe un producto con este código. Créalo primero.')
                else:
                    stock_antes = producto.stock
                    producto.stock += cantidad
                    producto.save(update_fields=['stock'])
                    MovimientoInventario.registrar(
                        producto=producto,
                        tipo=MovimientoInventario.Tipo.ENTRADA,
                        cantidad=cantidad,
                        stock_antes=stock_antes,
                        stock_despues=producto.stock,
                        usuario=request.user,
                        tienda=tienda_actual,
                        motivo=motivo,
                    )
                    messages.success(request, f'Entrada registrada: {cantidad} unidades para {producto.nombre}.')
                    return redirect('entrada_rapida')
    else:
        form = EntradaRapidaForm()

    return render(request, 'inventario/productos/entrada_rapida.html', {
        **get_config_context('Inventario', 'border-purple-600'),
        'form': form,
    })


@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
def exportar_productos_csv(request):
    productos, _ = _productos_filtrados(request)
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="inventario_productos.csv"'
    response.write('\ufeff')
    writer = csv.writer(response)
    writer.writerow(['codigo_barras', 'nombre', 'categoria', 'stock', 'stock_minimo', 'costo', 'precio', 'activo'])

    for producto in productos:
        precio = _precio_actual(producto)
        writer.writerow([
            producto.codigo_barras,
            producto.nombre,
            producto.categoria.nombre if producto.categoria else '',
            producto.stock,
            producto.stock_minimo,
            precio.costo if precio else '',
            precio.precio if precio else '',
            '1' if producto.activo else '0',
        ])

    return response


@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
@require_http_methods(["GET", "POST"])
def importar_productos_csv(request):
    tienda_actual = get_tienda_actual(request)
    resultado = None
    errores = []

    if request.method == 'POST':
        form = ImportarProductosForm(request.POST, request.FILES)
        if form.is_valid():
            creados = actualizados = movimientos = precios = 0
            archivo = TextIOWrapper(form.cleaned_data['archivo'].file, encoding='utf-8-sig')
            reader = csv.DictReader(archivo)
            columnas_requeridas = {'codigo_barras', 'nombre'}
            if not reader.fieldnames or not columnas_requeridas.issubset(set(reader.fieldnames)):
                errores.append('El CSV debe incluir al menos las columnas codigo_barras y nombre.')
            else:
                for numero_fila, row in enumerate(reader, start=2):
                    try:
                        codigo = (row.get('codigo_barras') or '').strip()
                        nombre = (row.get('nombre') or '').strip()
                        if not codigo or not nombre:
                            raise ValueError('Código y nombre son obligatorios.')

                        categoria = None
                        categoria_nombre = (row.get('categoria') or '').strip()
                        if categoria_nombre:
                            categoria, _ = Categoria.objects.get_or_create(nombre=categoria_nombre)

                        stock = _int_csv(row.get('stock'), 0)
                        stock_minimo = _int_csv(row.get('stock_minimo'), 5)
                        if stock < 0 or stock_minimo < 0:
                            raise ValueError('Stock y stock mínimo no pueden ser negativos.')

                        costo = _decimal_csv(row.get('costo'), Decimal('0.00'))
                        precio = _decimal_csv(row.get('precio'), None)
                        if costo is not None and costo < 0 or precio is not None and precio < 0:
                            raise ValueError('Costo y precio no pueden ser negativos.')

                        activo = _str_to_bool(row.get('activo', '1'))

                        with transaction.atomic():
                            producto = Producto.objects.select_for_update().filter(codigo_barras=codigo).first()
                            if producto:
                                stock_antes = producto.stock
                                producto.nombre = nombre
                                producto.categoria = categoria
                                producto.stock = stock
                                producto.stock_minimo = stock_minimo
                                producto.activo = activo
                                producto.full_clean()
                                producto.save(update_fields=['nombre', 'categoria', 'stock', 'stock_minimo', 'activo'])
                                actualizados += 1
                            else:
                                stock_antes = 0
                                producto = Producto.objects.create(
                                    codigo_barras=codigo,
                                    nombre=nombre,
                                    categoria=categoria,
                                    stock=stock,
                                    stock_minimo=stock_minimo,
                                    activo=activo,
                                )
                                creados += 1

                            if stock != stock_antes:
                                MovimientoInventario.registrar(
                                    producto=producto,
                                    tipo=MovimientoInventario.Tipo.ENTRADA if stock > stock_antes else MovimientoInventario.Tipo.AJUSTE,
                                    cantidad=stock - stock_antes,
                                    stock_antes=stock_antes,
                                    stock_despues=stock,
                                    usuario=request.user,
                                    tienda=tienda_actual,
                                    motivo='Importación CSV',
                                )
                                movimientos += 1

                            if precio is not None:
                                precio_anterior = _precio_actual(producto)
                                _guardar_precio_producto(producto, costo, precio, request.user, 'Importación CSV', tienda_actual)
                                if not precio_anterior or precio_anterior.costo != costo or precio_anterior.precio != precio:
                                    precios += 1
                    except (InvalidOperation, ValueError) as exc:
                        errores.append(f'Fila {numero_fila}: {exc}')

            resultado = {
                'creados': creados,
                'actualizados': actualizados,
                'movimientos': movimientos,
                'precios': precios,
            }
    else:
        form = ImportarProductosForm()

    return render(request, 'inventario/productos/importar_csv.html', {
        **get_config_context('Inventario', 'border-purple-600'),
        'form': form,
        'resultado': resultado,
        'errores': errores,
    })


@login_required
@permission_required('configuraciones.acceder_inventario', login_url='portal_principal')
def imprimir_etiquetas(request):
    ids = [id_producto for id_producto in request.GET.get('ids', '').split(',') if id_producto.isdigit()]
    if ids:
        productos = Producto.objects.select_related('precios').filter(id__in=ids).order_by('nombre')
    else:
        productos, _ = _productos_filtrados(request)
        productos = productos.filter(activo=True, precios__isnull=False)[:120]

    return render(request, 'inventario/productos/etiquetas.html', {
        'productos': productos,
    })
