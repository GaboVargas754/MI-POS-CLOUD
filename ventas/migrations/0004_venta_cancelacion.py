from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ventas', '0003_sesioncaja_venta_sesion'),
    ]

    operations = [
        migrations.AddField(
            model_name='venta',
            name='estado',
            field=models.CharField(choices=[('ACTIVA', 'Activa'), ('CANCELADA', 'Cancelada')], default='ACTIVA', max_length=12),
        ),
        migrations.AddField(
            model_name='venta',
            name='motivo_cancelacion',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='venta',
            name='fecha_cancelacion',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='venta',
            name='cancelado_por',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='ventas_canceladas', to=settings.AUTH_USER_MODEL),
        ),
    ]
