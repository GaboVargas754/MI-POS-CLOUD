from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Sum
from ventas.models import SesionCaja, Venta

def abrir_caja(request):
    if SesionCaja.objects.filter(cajero=request.user, estado=True).exists():
        return redirect('pantalla_pos')

    if request.method == 'POST':
        fondo = request.POST.get('fondo_inicial', 0)
        SesionCaja.objects.create(
            cajero=request.user,
            fondo_inicial=fondo,
            estado=True
        )
        return redirect('pantalla_pos')

    return render(request, 'ventas/abrir_caja.html')

def cerrar_caja(request):
    sesion = get_object_or_404(SesionCaja, cajero=request.user, estado=True)
    ventas_efectivo = Venta.objects.filter(sesion=sesion, metodo_pago='EFE').aggregate(Sum('total'))['total__sum'] or 0
    esperado_en_caja = float(sesion.fondo_inicial) + float(ventas_efectivo)

    if request.method == 'POST':
        efectivo_contado = request.POST.get('efectivo_cierre', 0)

        sesion.efectivo_cierre = efectivo_contado
        sesion.fecha_cierre = timezone.now()
        sesion.estado = False
        sesion.save()

        return redirect('dashboard')

    contexto = {
        'sesion': sesion,
        'ventas_efectivo': ventas_efectivo,
        'esperado_en_caja': esperado_en_caja,
    }
    return render(request, 'ventas/cerrar_caja.html', contexto)
