import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0003_alter_document_uuid'),
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentTemplate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='Название шаблона')),
                ('document_type', models.CharField(
                    choices=[
                        ('contract', 'Договор'),
                        ('power_of_attorney', 'Доверенность'),
                        ('court_filing', 'Судебное обращение'),
                        ('evidence', 'Доказательство'),
                        ('correspondence', 'Переписка'),
                        ('other', 'Прочее'),
                    ],
                    default='other', max_length=30, verbose_name='Тип документа',
                )),
                ('file', models.FileField(upload_to='document_templates/', verbose_name='Файл шаблона (.docx)')),
                ('description', models.TextField(blank=True, verbose_name='Описание')),
                ('created_at', models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now)),
            ],
            options={
                'verbose_name': 'Шаблон документа',
                'verbose_name_plural': 'Шаблоны документов',
                'ordering': ['name'],
            },
        ),
    ]
