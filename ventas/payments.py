from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db.models import Sum


METODOS_DETALLE = {'EFE', 'TAR', 'TRA'}
CENTAVOS = Decimal('0.01')


def dinero(value, campo='monto'):
    try:
        amount = Decimal(str(value if value not in [None, ''] else '0'))
    except (InvalidOperation, ValueError):
        raise ValueError(f'Captura un {campo} válido.')

    if not amount.is_finite() or amount < 0:
        raise ValueError(f'Captura un {campo} válido.')
    return amount.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def calcular_propina(subtotal, porcentaje):
    subtotal = dinero(subtotal, 'subtotal')
    porcentaje = dinero(porcentaje, 'porcentaje de propina')
    if porcentaje > Decimal('100.00'):
        raise ValueError('El porcentaje de propina no puede ser mayor a 100%.')
    return (subtotal * porcentaje / Decimal('100')).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def calcular_desglose_pago(*, total, metodo_pago, pago_recibido=None, pago_efectivo=None, pago_tarjeta=None, pago_transferencia=None):
    total = dinero(total, 'total a cobrar')
    metodo_pago = metodo_pago or 'EFE'

    if metodo_pago in METODOS_DETALLE:
        if metodo_pago == 'EFE':
            efectivo_recibido = dinero(pago_recibido, 'pago recibido')
            if efectivo_recibido == 0:
                efectivo_recibido = total
            if efectivo_recibido < total:
                raise ValueError('El pago recibido es menor al total.')
            return {
                'metodo_pago': 'EFE',
                'pago_recibido': efectivo_recibido,
                'cambio': efectivo_recibido - total,
                'pagos': [{'metodo_pago': 'EFE', 'monto': total}] if total > 0 else [],
            }

        return {
            'metodo_pago': metodo_pago,
            'pago_recibido': total,
            'cambio': Decimal('0.00'),
            'pagos': [{'metodo_pago': metodo_pago, 'monto': total}] if total > 0 else [],
        }

    if metodo_pago != 'MIX':
        raise ValueError('Selecciona un método de pago válido.')

    efectivo = dinero(pago_efectivo, 'pago en efectivo')
    tarjeta = dinero(pago_tarjeta, 'pago con tarjeta')
    transferencia = dinero(pago_transferencia, 'pago por transferencia')
    no_efectivo = tarjeta + transferencia
    pago_total = efectivo + no_efectivo

    if no_efectivo > total:
        raise ValueError('Tarjeta y transferencia no pueden exceder el total a cobrar.')
    if pago_total < total:
        raise ValueError('La suma de pagos es menor al total a cobrar.')

    cambio = pago_total - total
    efectivo_aplicado = total - no_efectivo
    if efectivo_aplicado < 0:
        efectivo_aplicado = Decimal('0.00')
    if efectivo_aplicado > efectivo:
        raise ValueError('La suma de pagos es menor al total a cobrar.')

    pagos = []
    if efectivo_aplicado > 0:
        pagos.append({'metodo_pago': 'EFE', 'monto': efectivo_aplicado})
    if tarjeta > 0:
        pagos.append({'metodo_pago': 'TAR', 'monto': tarjeta})
    if transferencia > 0:
        pagos.append({'metodo_pago': 'TRA', 'monto': transferencia})

    if not pagos:
        raise ValueError('Captura al menos un pago.')

    metodo_final = pagos[0]['metodo_pago'] if len(pagos) == 1 else 'MIX'
    return {
        'metodo_pago': metodo_final,
        'pago_recibido': pago_total,
        'cambio': cambio,
        'pagos': pagos,
    }


def registrar_pagos_venta(venta, pagos):
    from ventas.models import PagoVenta

    PagoVenta.objects.filter(venta=venta).delete()
    PagoVenta.objects.bulk_create([
        PagoVenta(venta=venta, metodo_pago=pago['metodo_pago'], monto=pago['monto'])
        for pago in pagos
        if pago['monto'] > 0
    ])


def total_pagos_por_metodo(ventas, metodo_pago):
    from ventas.models import PagoVenta

    total_pagos = PagoVenta.objects.filter(venta__in=ventas, metodo_pago=metodo_pago).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    total_legacy = ventas.filter(pagos__isnull=True, metodo_pago=metodo_pago).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    return total_pagos + total_legacy
