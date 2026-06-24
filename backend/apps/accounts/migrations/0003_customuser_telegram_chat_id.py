from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_auto_20260417_2027'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='telegram_chat_id',
            field=models.CharField(
                blank=True,
                help_text='Для получения уведомлений в Telegram',
                max_length=50,
                verbose_name='Telegram chat ID',
            ),
        ),
    ]
