from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_spmwithdrawconfirmation"),
    ]

    operations = [
        migrations.AddField(
            model_name="spmwithdrawconfirmation",
            name="user_name",
            field=models.CharField(blank=True, db_index=True, default="", max_length=255),
        ),
        migrations.AlterField(
            model_name="spmwithdrawconfirmation",
            name="user_id",
            field=models.PositiveIntegerField(blank=True, db_index=True, null=True),
        ),
    ]
