from django.db import migrations, models


def renombrar_permiso_sistema(apps, schema_editor):
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    content_type = ContentType.objects.filter(
        app_label='configuraciones',
        model='configuracionsistema',
    ).first()
    if not content_type:
        return

    Permission.objects.filter(
        content_type=content_type,
        codename='acceder_configuraciones',
    ).update(name='Módulo de Sistema: Usuarios, Roles y Preferencias')


class Migration(migrations.Migration):

    dependencies = [
        ('configuraciones', '0003_remove_configuracionsistema_pagina_inicio_and_more'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='configuracionsistema',
            options={
                'permissions': [
                    ('acceder_ventas', 'Módulo de Ventas: Acceso al Punto de Venta y Cobro'),
                    ('acceder_inventario', 'Módulo de Inventario: Gestión de Productos y Categorías'),
                    ('acceder_configuraciones', 'Módulo de Sistema: Usuarios, Roles y Preferencias'),
                ],
                'verbose_name': 'Configuración del Sistema',
            },
        ),
        migrations.RunPython(renombrar_permiso_sistema, migrations.RunPython.noop),
    ]
