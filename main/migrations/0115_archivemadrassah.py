# Generated manually for ArchiveMadrassah

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0114_alter_jamat_centre'),
    ]

    operations = [
        migrations.CreateModel(
            name='ArchiveMadrassah',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                (
                    'archive_type',
                    models.CharField(
                        choices=[('Madrassah', 'Madrassah'), ('Autre', 'Autre')],
                        default='Madrassah',
                        max_length=20,
                        verbose_name="Type d'archive",
                    ),
                ),
                (
                    'raison',
                    models.CharField(
                        choices=[
                            ('Renvoyé', 'Renvoyé'),
                            ('Démission', 'Démission'),
                            ('Transfert', 'Transfert'),
                            ('Autre', 'Autre'),
                        ],
                        default='Autre',
                        max_length=20,
                        verbose_name="Raison d'archive",
                    ),
                ),
                ('archived_at', models.DateField(auto_now_add=True, verbose_name="Date d'archive")),
                (
                    'madrassah',
                    models.ForeignKey(
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to='main.madrassah',
                        verbose_name='Madrassah',
                    ),
                ),
            ],
        ),
    ]
