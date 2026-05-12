from configuraciones.models import PerfilUsuario, PuntoVenta, Tienda


def get_tienda_principal():
    tienda, _ = Tienda.objects.get_or_create(
        codigo='PRINCIPAL',
        defaults={
            'nombre': 'Sucursal Principal',
            'direccion': '',
            'telefono': '',
            'activa': True,
        },
    )
    PuntoVenta.objects.get_or_create(
        tienda=tienda,
        codigo='CAJA-1',
        defaults={'nombre': 'Caja 1', 'activo': True},
    )
    return tienda


def get_perfil_usuario(user):
    tienda = get_tienda_principal()
    punto_venta = PuntoVenta.objects.filter(tienda=tienda, activo=True).order_by('id').first()
    perfil, _ = PerfilUsuario.objects.get_or_create(
        usuario=user,
        defaults={
            'tienda': tienda,
            'punto_venta': punto_venta,
            'puede_ver_todas_las_tiendas': bool(user.is_superuser),
        },
    )
    if perfil.punto_venta is None:
        perfil.punto_venta = PuntoVenta.objects.filter(tienda=perfil.tienda, activo=True).order_by('id').first()
        perfil.save(update_fields=['punto_venta'])
    return perfil


def get_tienda_actual(request):
    return get_perfil_usuario(request.user).tienda


def get_punto_venta_actual(request):
    return get_perfil_usuario(request.user).punto_venta


def tiendas_visibles(user):
    perfil = get_perfil_usuario(user)
    if user.is_superuser or perfil.puede_ver_todas_las_tiendas:
        return Tienda.objects.filter(activa=True).order_by('nombre')
    return Tienda.objects.filter(id=perfil.tienda_id)
