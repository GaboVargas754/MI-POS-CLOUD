from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from core.utils import get_config_context
from configuraciones.utils import get_punto_venta_actual, get_tienda_actual
from ventas.models import SesionCaja, Venta
from ventas.payments import dinero, total_pagos_por_metodo
from ventas.views.carrito import OPERAR_POS_PERMISSION

CAJA_PERMISSION = 'configuraciones.abrir_cerrar_caja'


def _contexto_pos(**extra_context):
    return {
        **get_config_context('POS', 'border-green-600'),
        **extra_context,
    }

@login_required
@permission_required(CAJA_PERMISSION, login_url='portal_principal')
@require_http_methods(["GET", "POST"])
def abrir_caja(request):
    tienda_actual = get_tienda_actual(request)
    filtro_tienda = Q(tienda=tienda_actual) | Q(tienda__isnull=True)
    if SesionCaja.objects.filter(filtro_tienda, cajero=request.user, estado=True).exists():
        messages.info(request, 'Ya tienes un turno abierto. Continúa desde el POS.')
        return redirect('pantalla_pos')

    if request.method == 'POST':
        try:
            fondo = dinero(request.POST.get('fondo_inicial'), 'fondo inicial')
        except ValueError:
            return render(request, 'ventas/abrir_caja.html', _contexto_pos(error='Ingresa un fondo inicial válido.'))

        SesionCaja.objects.create(
            cajero=request.user,
            tienda=tienda_actual,
            punto_venta=get_punto_venta_actual(request),
            fondo_inicial=fondo,
            estado=True
        )
        messages.success(request, 'Turno abierto. Ya puedes comenzar a vender.')
        return redirect('pantalla_pos')

    return render(request, 'ventas/abrir_caja.html', _contexto_pos())

@login_required
@permission_required(CAJA_PERMISSION, login_url='portal_principal')
@require_http_methods(["GET", "POST"])
def cerrar_caja(request):
    tienda_actual = get_tienda_actual(request)
    filtro_tienda = Q(tienda=tienda_actual) | Q(tienda__isnull=True)
    sesion = SesionCaja.objects.filter(filtro_tienda, cajero=request.user, estado=True).first()
    if not sesion:
        messages.warning(request, 'No hay un turno abierto. Abre caja antes de continuar.')
        return redirect('abrir_caja')

    ventas_activas = Venta.objects.filter(Q(tienda=tienda_actual) | Q(tienda__isnull=True), sesion=sesion, estado='ACTIVA')
    ventas_efectivo = total_pagos_por_metodo(ventas_activas, 'EFE')
    esperado_en_caja = sesion.fondo_inicial + ventas_efectivo

    if request.method == 'POST':
        try:
            efectivo_raw = request.POST.get('efectivo_cierre')
            efectivo_valor = Decimal(str(efectivo_raw if efectivo_raw not in [None, ''] else '0'))
        except ValueError:
            return render(request, 'ventas/cerrar_caja.html', _contexto_pos(
                sesion=sesion,
                ventas_efectivo=ventas_efectivo,
                esperado_en_caja=esperado_en_caja,
                error='Ingresa un efectivo de cierre válido.',
            ))
        except InvalidOperation:
            return render(request, 'ventas/cerrar_caja.html', _contexto_pos(
                sesion=sesion,
                ventas_efectivo=ventas_efectivo,
                esperado_en_caja=esperado_en_caja,
                error='Ingresa un efectivo de cierre válido.',
            ))

        if not efectivo_valor.is_finite():
            return render(request, 'ventas/cerrar_caja.html', _contexto_pos(
                sesion=sesion,
                ventas_efectivo=ventas_efectivo,
                esperado_en_caja=esperado_en_caja,
                error='Ingresa un efectivo de cierre válido.',
            ))

        if efectivo_valor < 0:
            return render(request, 'ventas/cerrar_caja.html', _contexto_pos(
                sesion=sesion,
                ventas_efectivo=ventas_efectivo,
                esperado_en_caja=esperado_en_caja,
                error='El efectivo de cierre no puede ser negativo.',
            ))

        efectivo_contado = dinero(efectivo_valor, 'efectivo de cierre')

        sesion.efectivo_cierre = efectivo_contado
        sesion.fecha_cierre = timezone.now()
        sesion.estado = False
        sesion.save()

        messages.success(request, 'Turno cerrado correctamente.')
        return redirect('dashboard')

    contexto = _contexto_pos(
        sesion=sesion,
        ventas_efectivo=ventas_efectivo,
        esperado_en_caja=esperado_en_caja,
    )
    return render(request, 'ventas/cerrar_caja.html', contexto)
