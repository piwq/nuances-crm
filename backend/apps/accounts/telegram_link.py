"""Привязка Telegram-аккаунта к пользователю CRM через одноразовый токен."""
import secrets
from datetime import timedelta

from django.utils import timezone

from .models import TelegramLinkToken

TOKEN_TTL = timedelta(minutes=15)


def create_link_token(user):
    """Одноразовый токен для deep-link (?start=<token>, лимит Telegram — 64 символа)."""
    TelegramLinkToken.objects.filter(user=user).delete()
    token = secrets.token_urlsafe(24)  # 32 url-safe символа
    TelegramLinkToken.objects.create(user=user, token=token)
    return token


def use_link_token(token, chat_id):
    """Погасить токен: привязать chat_id, вернуть пользователя (или None)."""
    try:
        row = TelegramLinkToken.objects.select_related('user').get(token=token)
    except TelegramLinkToken.DoesNotExist:
        return None
    if row.created_at < timezone.now() - TOKEN_TTL:
        row.delete()
        return None
    user = row.user
    user.telegram_chat_id = str(chat_id)
    user.save(update_fields=['telegram_chat_id'])
    TelegramLinkToken.objects.filter(user=user).delete()
    return user
