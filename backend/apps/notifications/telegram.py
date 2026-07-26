"""Отправка сообщений в Telegram через Bot API.

Использует только стандартную библиотеку (urllib), без доп. зависимостей.
Любые ошибки сети/API проглатываются: уведомление в БД/WS не должно падать
из-за недоступности Telegram.
"""
import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

_BOT_USERNAME = None


def get_bot_username():
    """Username бота через getMe (кэшируется на процесс); '' если бот не настроен."""
    global _BOT_USERNAME
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token:
        return ''
    if _BOT_USERNAME:
        return _BOT_USERNAME
    try:
        with urllib.request.urlopen(
                f'https://api.telegram.org/bot{token}/getMe', timeout=5) as resp:
            data = json.load(resp)
        _BOT_USERNAME = data['result']['username']
    except Exception as e:  # noqa: BLE001
        logger.warning('getMe не удался: %s', e)
        return ''
    return _BOT_USERNAME


def send_telegram_message(chat_id, text):
    """Отправить сообщение пользователю. Возвращает True при успехе."""
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '')
    if not token or not chat_id:
        return False

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = urllib.parse.urlencode({
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': 'true',
    }).encode()

    try:
        req = urllib.request.Request(url, data=payload)
        with urllib.request.urlopen(req, timeout=5) as resp:
            return 200 <= resp.status < 300
    except Exception as e:  # noqa: BLE001 — Telegram недоступен не критично
        logger.warning('Не удалось отправить сообщение в Telegram: %s', e)
        return False
