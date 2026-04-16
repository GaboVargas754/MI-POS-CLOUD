from django.shortcuts import render, get_object_or_404
from ventas.models import Producto

def agregar_al_carrito(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    carrito = request.session.get('carrito', {})
    producto_id_str = str(producto_id)

    if producto_id_str in carrito:
        carrito[producto_id_str]['cantidad'] += 1
    else:
        carrito[producto_id_str] = {
            'nombre': producto.nombre,
            'precio': float(producto.precio),
            'cantidad': 1,
        }

    request.session['carrito'] = carrito
    total = sum(item['precio'] * item['cantidad'] for item in carrito.values())

    contexto = {
        'carrito': carrito,
        'total': total
    }
    return render(request, 'ventas/partials/carrito.html', contexto)

def vaciar_carrito(request):
    request.session['carrito'] = {}
    contexto = {
        'carrito': {},
        'total': 0
    }
    return render(request, 'ventas/partials/carrito.html', contexto)

def eliminar_item(request, producto_id):
    carrito = request.session.get('carrito', {})
    producto_id_str = str(producto_id)

    if producto_id_str in carrito:
        del carrito[producto_id_str]
        request.session['carrito'] = carrito

    total = sum(item['precio'] * item['cantidad'] for item in carrito.values())
    contexto = {
        'carrito': carrito,
        'total': total
    }
    return render(request, 'ventas/partials/carrito.html', contexto)

def restar_item(request, producto_id):
    carrito = request.session.get('carrito', {})
    producto_id_str = str(producto_id)

    if producto_id_str in carrito:
        carrito[producto_id_str]['cantidad'] -= 1

        if carrito[producto_id_str]['cantidad'] <= 0:
            del carrito[producto_id_str]
        request.session['carrito'] = carrito

    total = sum(item['precio'] * item['cantidad'] for item in carrito.values())

    contexto = {
        'carrito': carrito,
        'total': total
    }
    return render(request, 'ventas/partials/carrito.html', contexto)
