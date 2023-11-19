# Generated by Django 4.2.7 on 2023-11-19 13:32

from django.db import migrations, models
import django.db.models.deletion
import django_model_signals.models
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Organization',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(default=None, max_length=64)),
            ],
            options={
                'db_table': 'django_jsonapi_framework__auth__organization',
            },
            bases=(django_model_signals.models.PostFullCleanErrorSignalMixin, django_model_signals.models.PreFullCleanSignalMixin, models.Model),
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(default=None, max_length=254, unique=True)),
                ('is_email_confirmed', models.BooleanField(default=False)),
                ('password', models.CharField(default=None, max_length=128)),
                ('organization', models.ForeignKey(default=None, on_delete=django.db.models.deletion.PROTECT, to='django_jsonapi_framework_auth.organization')),
            ],
            options={
                'db_table': 'django_jsonapi_framework__auth__user',
            },
            bases=(django_model_signals.models.PreFullCleanSignalMixin, models.Model),
        ),
        migrations.CreateModel(
            name='UserEmailConfirmation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(default=None, editable=False, max_length=254)),
                ('token', models.CharField(default=None, editable=False, max_length=128)),
                ('expired_at', models.DateTimeField(default=None, editable=False)),
                ('user', models.ForeignKey(default=None, editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='+', to='django_jsonapi_framework_auth.user')),
            ],
            options={
                'db_table': 'django_jsonapi_framework__auth__user_email_confirmation',
            },
            bases=(django_model_signals.models.PreFullCleanSignalMixin, django_model_signals.models.PostFullCleanSignalMixin, models.Model),
        ),
        migrations.AddField(
            model_name='organization',
            name='owner',
            field=models.OneToOneField(blank=True, default=None, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='owner_organization', to='django_jsonapi_framework_auth.user'),
        ),
    ]
