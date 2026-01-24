from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0015_currencyconfig"),
    ]

    operations = [
        migrations.DeleteModel(
            name="CurrencyConfig",
        ),
    ]
