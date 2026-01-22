from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_spmwithdrawconfirmation_username"),
    ]

    operations = [
        migrations.CreateModel(
            name="CurrencyConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("currency", models.FloatField(default=1.0)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Курс валюты",
                "verbose_name_plural": "Курсы валют",
            },
        ),
    ]
