# Generated by Django 5.1.4 on 2025-01-26 15:28

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_remove_testcase_url_alter_testcase_testcase_priority_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('url', models.URLField()),
                ('project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_links', to='api.project')),
            ],
        ),
    ]
