# Generated manually for pagos_banco app

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='TransaccionPagoMovil',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('id_cliente', models.CharField(blank=True, db_index=True, max_length=20, null=True)),
                ('monto_consultado', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('telefono_comercio', models.CharField(blank=True, max_length=15, null=True)),
                ('timestamp_consulta', models.DateTimeField(auto_now_add=True)),
                ('referencia', models.CharField(blank=True, db_index=True, max_length=30, null=True, unique=True)),
                ('monto_notificado', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True)),
                ('telefono_emisor', models.CharField(blank=True, max_length=15, null=True)),
                ('banco_emisor', models.CharField(blank=True, max_length=10, null=True)),
                ('concepto', models.CharField(blank=True, max_length=100, null=True)),
                ('timestamp_notificacion', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('PENDIENTE', 'Pendiente de Pago'), ('CONSULTADO', 'Consultado por Banco'), ('RECHAZADO', 'Rechazado por Comercio'), ('CONFIRMADO', 'Pago Confirmado'), ('ERROR', 'Error')], default='PENDIENTE', max_length=20)),
            ],
        ),
    ]

