# Generated by Django 4.0.4 on 2022-05-12 17:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dbmanageapp', '0004_delete_dbupdatechk'),
    ]

    operations = [
        migrations.CreateModel(
            name='ChkDbReset',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chk_dbreset', models.CharField(max_length=15)),
                ('chk_dbtime', models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]