# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-06-06 09:34
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SitesApp', '0008_auto_20180606_1308'),
    ]

    operations = [
        migrations.AlterField(
            model_name='chatrecord',
            name='crTopic',
            field=models.IntegerField(),
        ),
        migrations.AlterField(
            model_name='chatrecord',
            name='crType',
            field=models.IntegerField(),
        ),
    ]
