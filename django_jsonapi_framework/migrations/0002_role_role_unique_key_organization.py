# Generated by Django 4.2 on 2023-04-07 16:15

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('django_jsonapi_framework', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('key', models.CharField(default=None, max_length=64)),
                ('organization', models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='django_jsonapi_framework.organization')),
            ],
            options={
                'db_table': 'django_jsonapi_framework__roles',
            },
        ),
        migrations.AddConstraint(
            model_name='role',
            constraint=models.UniqueConstraint(fields=('key', 'organization'), name='unique_key_organization'),
        ),
    ]