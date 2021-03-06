# -*- coding: utf-8 -*-
# Generated by Django 1.11.7 on 2018-06-19 11:20
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('SitesApp', '0016_auto_20180613_1628'),
    ]

    operations = [
        migrations.AlterField(
            model_name='review',
            name='rRemark',
            field=models.IntegerField(default=1, verbose_name='备注(0:已办、1:待办、2:计划、3:归档)'),
        ),
        migrations.AlterField(
            model_name='review',
            name='rmDateTime',
            field=models.DateTimeField(auto_now_add=True, verbose_name='修改时间'),
        ),
    ]
