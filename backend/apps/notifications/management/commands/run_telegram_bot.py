"""Запуск Telegram-бота (long polling). Отдельный compose-сервис `bot`."""
import asyncio
import time

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run the CRM Telegram bot (aiogram long polling)'

    def handle(self, *args, **options):
        token = settings.TELEGRAM_BOT_TOKEN
        if not token:
            # не выходим: при restart-политике пустой токен дал бы рестарт-цикл
            self.stdout.write(self.style.WARNING(
                'TELEGRAM_BOT_TOKEN пуст — бот в режиме ожидания. '
                'Заполните токен в .env и пересоздайте сервис: docker compose up -d bot'))
            while True:
                time.sleep(3600)

        from apps.notifications.bot import run_polling
        self.stdout.write(self.style.SUCCESS('Запускаю Telegram-бота (polling)...'))
        asyncio.run(run_polling(token))
