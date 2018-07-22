# Generated by Django 2.0.6 on 2018-06-12 08:47

from django.db import migrations, models
import tinymce.models


class Migration(migrations.Migration):

    dependencies = [
        ('SitesApp', '0012_auto_20180611_2014'),
    ]

    operations = [
        migrations.RenameField(
            model_name='review',
            old_name='rDateTime',
            new_name='rcDateTime',
        ),
        migrations.RemoveField(
            model_name='review',
            name='rInfo',
        ),
        migrations.AddField(
            model_name='review',
            name='rContent',
            field=tinymce.models.HTMLField(default=None),
        ),
        migrations.AddField(
            model_name='review',
            name='rmDateTime',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
