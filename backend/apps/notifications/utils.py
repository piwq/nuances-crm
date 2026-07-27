from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import IntegrityError

from .models import Notification


def create_notification(user, title, body='', link='', key='', telegram=True, tg_buttons=None):
    """Create a Notification and push it to the user's WS group.
    If key is given and a notification with that key already exists, skip.

    telegram=False — только колокольчик/WS, без дубля в Telegram (например,
    когда красивый Telegram-вариант отправляется отдельно).
    tg_buttons — inline-клавиатура Bot API для telegram-копии уведомления.
    """
    if key and Notification.objects.filter(user=user, key=key).exists():
        return None

    try:
        notif = Notification.objects.create(
            user=user, title=title, body=body, link=link, key=key)
    except IntegrityError:
        return None  # параллельный прогон уже создал это уведомление
    _push_ws(notif)
    if telegram:
        _push_telegram(notif, tg_buttons)
    return notif


def _push_telegram(notification, tg_buttons=None):
    chat_id = getattr(notification.user, 'telegram_chat_id', '')
    if not chat_id:
        return
    from html import escape
    from .telegram import send_telegram_message
    # parse_mode=HTML: без экранирования «&», «<» в названиях дел ломают отправку
    text = f'<b>{escape(notification.title)}</b>'
    if notification.body:
        text += f'\n{escape(notification.body)}'
    reply_markup = {'inline_keyboard': tg_buttons} if tg_buttons else None
    send_telegram_message(chat_id, text, reply_markup=reply_markup)


def _push_ws(notification):
    channel_layer = get_channel_layer()
    if not channel_layer:
        return
    try:
        async_to_sync(channel_layer.group_send)(
            f'notifications_{notification.user_id}',
            {
                'type': 'notify',
                'data': {
                    'id': notification.id,
                    'title': notification.title,
                    'body': notification.body,
                    'link': notification.link,
                    'is_read': False,
                    'created_at': notification.created_at.isoformat(),
                },
            },
        )
    except Exception:
        pass  # WS unavailable (e.g. in management commands without ASGI server)
