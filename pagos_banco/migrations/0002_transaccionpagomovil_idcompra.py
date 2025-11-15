# Generated migration to add idCompra field to TransaccionPagoMovil

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('pagos_banco', '0001_initial'),
        ('Rifa', '0027_cliente_and_comprador_update'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaccionpagomovil',
            name='idCompra',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='transacciones_pago_movil', to='Rifa.compra', db_index=True),
        ),
    ]

