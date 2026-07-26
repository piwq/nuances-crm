"""Утренняя Telegram-сводка: события, задачи и горящие сроки на сегодня.

Вызывается планировщиком каждые полчаса; сама решает, пора ли слать
(будни, час DIGEST_HOUR по локальному времени) и дедуплицируется по дню
через Notification.key. --force игнорирует расписание (для ручного теста).
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import CustomUser
from apps.notifications.bot import today_digest_text
from apps.notifications.telegram import send_telegram_message
from apps.notifications.utils import create_notification

DIGEST_HOUR = 7  # локальное время (Europe/Moscow)


class Command(BaseCommand):
    help = 'Send the morning Telegram digest to all linked users'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true',
                            help='отправить сейчас, игнорируя день недели и час')

    def handle(self, *args, **options):
        now = timezone.localtime()
        if not options['force']:
            if now.weekday() >= 5 or now.hour != DIGEST_HOUR:
                self.stdout.write('Digest: вне окна отправки, пропуск')
                return

        sent = 0
        users = CustomUser.objects.filter(is_active=True).exclude(telegram_chat_id='')
        for user in users:
            key = f'digest_{user.id}_{now.date()}'
            # запись в колокольчик служит и дедупликацией на день;
            # telegram=False — красивый MarkdownV2-вариант шлём сами
            notif = create_notification(
                user=user,
                title='Утренняя сводка отправлена в Telegram',
                body='',
                link='/dashboard',
                key=key,
                telegram=False,
            )
            if notif is None:
                continue  # сегодня уже отправляли
            text = today_digest_text(user)
            send_telegram_message(user.telegram_chat_id, text, parse_mode='MarkdownV2')
            sent += 1

        self.stdout.write(self.style.SUCCESS(f'Digest sent to {sent} users'))
