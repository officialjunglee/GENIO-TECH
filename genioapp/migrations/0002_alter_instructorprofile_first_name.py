# Generated by Django 4.2.7 on 2023-11-22 03:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('genioapp', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instructorprofile',
            name='first_name',
            field=models.CharField(default='first_name', max_length=100),
        ),
    ]
