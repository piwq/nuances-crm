from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from .models import Notification


def create_notification(user, title, body='', link='', key=''):
    """Create a Notification and push it to the user's WS group.
    If key is given and a notification with that key already exists, skip."""
    if key and Notification.objects.filter(user=user, key=key).exists():
        return None

    notif = Notification.objects.create(user=user, title=title, body=body, link=link, key=key)
    _push_ws(notif)
    _push_telegram(notif)
    return notif


def _push_telegram(notification):
    chat_id = getattr(notification.user, 'telegram_chat_id', '')
    if not chat_id:
        return
    from .telegram import send_telegram_message
    text = f'<b>{notification.title}</b>'
    if notification.body:
        text += f'\n{notification.body}'
    send_telegram_message(chat_id, text)


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
