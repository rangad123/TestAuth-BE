# Generated by Django 5.1.4 on 2025-03-16 10:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0018_project_created_at_project_updated_at_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='teststep',
            name='teststep_result',
            field=models.CharField(choices=[('passed', 'Passed'), ('failed', 'Failed'), ('not_executed', 'Not Executed')], default='not_executed', max_length=15),
        ),
    ]
