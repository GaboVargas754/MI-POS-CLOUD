from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import render, redirect
from django.utils import timezone
from django.db.models import Sum
from django.views.decorators.http import require_http_methods
from core.utils import get_config_context
from ventas.models import SesionCaja, Venta
from ventas.views.carrito import VENTAS_PERMISSION


def _contexto_pos(**extra_context):
    return {
        **get_config_context('POS', 'border-green-600'),
        **extra_context,
    }

@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
@require_http_methods(["GET", "POST"])
def abrir_caja(request):
    if SesionCaja.objects.filter(cajero=request.user, estado=True).exists():
        messages.info(request, 'Ya tienes un turno abierto. Continúa desde el POS.')
        return redirect('pantalla_pos')

    if request.method == 'POST':
        try:
            fondo = Decimal(request.POST.get('fondo_inicial') or '0')
        except InvalidOperation:
            return render(request, 'ventas/abrir_caja.html', _contexto_pos(error='Ingresa un fondo inicial válido.'))

        SesionCaja.objects.create(
            cajero=request.user,
            fondo_inicial=fondo,
            estado=True
        )
        messages.success(request, 'Turno abierto. Ya puedes comenzar a vender.')
        return redirect('pantalla_pos')

    return render(request, 'ventas/abrir_caja.html', _contexto_pos())

@login_required
@permission_required(VENTAS_PERMISSION, login_url='portal_principal')
@require_http_methods(["GET", "POST"])
def cerrar_caja(request):
    sesion = SesionCaja.objects.filter(cajero=request.user, estado=True).first()
    if not sesion:
        messages.warning(request, 'No hay un turno abierto. Abre caja antes de continuar.')
        return redirect('abrir_caja')

    ventas_efectivo = Venta.objects.filter(sesion=sesion, metodo_pago='EFE', estado='ACTIVA').aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
    esperado_en_caja = sesion.fondo_inicial + ventas_efectivo

    if request.method == 'POST':
        try:
            efectivo_contado = Decimal(request.POST.get('efectivo_cierre') or '0')
        except InvalidOperation:
            return render(request, 'ventas/cerrar_caja.html', _contexto_pos(
                sesion=sesion,
                ventas_efectivo=ventas_efectivo,
                esperado_en_caja=esperado_en_caja,
                error='Ingresa un efectivo de cierre válido.',
            ))

        if efectivo_contado < 0:
            return render(request, 'ventas/cerrar_caja.html', _contexto_pos(
                sesion=sesion,
                ventas_efectivo=ventas_efectivo,
                esperado_en_caja=esperado_en_caja,
                error='El efectivo de cierre no puede ser negativo.',
            ))

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
