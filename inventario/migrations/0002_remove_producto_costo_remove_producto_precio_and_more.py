import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('inventario', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='producto',
            name='costo',
        ),
        migrations.RemoveField(
            model_name='producto',
            name='precio',
        ),
        migrations.CreateModel(
            name='PrecioProducto',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('costo', models.DecimalField(decimal_places=2, max_digits=10)),
                ('precio', models.DecimalField(decimal_places=2, max_digits=10)),
                ('margen_ganancia', models.DecimalField(decimal_places=2, editable=False, max_digits=10)),
                ('fecha_ultimo_cambio', models.DateTimeField(auto_now=True)),
                ('producto', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='precios', to='inventario.producto')),
            ],
        ),
    ]
