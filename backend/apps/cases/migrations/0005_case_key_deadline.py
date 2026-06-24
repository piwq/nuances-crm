from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cases', '0004_casenote'),
    ]

    operations = [
        migrations.AddField(
            model_name='case',
            name='key_deadline',
            field=models.DateField(blank=True, null=True, verbose_name='Ключевой процессуальный срок'),
        ),
        migrations.AddField(
            model_name='case',
            name='key_deadline_note',
            field=models.CharField(
                blank=True,
                help_text='Напр.: срок исковой давности, подача апелляции',
                max_length=255,
                verbose_name='Описание срока',
            ),
        ),
    ]
