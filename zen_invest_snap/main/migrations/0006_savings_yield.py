from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_dailysnapshot_currency_normalized_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='asset',
            name='asset_type',
            field=models.CharField(
                choices=[
                    ('STOCK', 'Stock'),
                    ('CRYPTO', 'Cryptocurrency'),
                    ('FIAT', 'Fiat Currency'),
                    ('ETF', 'ETF'),
                    ('BOND', 'Bond'),
                    ('SAVINGS', 'Savings / Yield account'),
                ],
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='asset',
            name='annual_yield_rate',
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                help_text='Annual simple interest rate, as a percentage.',
                max_digits=5,
            ),
        ),
    ]
