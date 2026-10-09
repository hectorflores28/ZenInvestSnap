from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0006_savings_yield'),
    ]

    operations = [
        migrations.CreateModel(
            name='SavingsRateChange',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                ('effective_date', models.DateField()),
                ('annual_yield_rate', models.DecimalField(decimal_places=2, max_digits=5)),
                (
                    'asset',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='savings_rate_changes',
                        to='main.asset',
                    ),
                ),
            ],
            options={
                'ordering': ['effective_date', 'pk'],
                'unique_together': {('asset', 'effective_date')},
            },
        ),
    ]
