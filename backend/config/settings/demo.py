"""Настройки для локального полного стека через docker compose.

Идентичны production, но рассчитаны на доступ по обычному HTTP на localhost
(демо/разработка): отключены HTTPS-only механизмы, которые иначе ломают вход
в админку и навсегда переключают localhost на https через HSTS.
"""
from .production import *

# Сервится по http://localhost — снимаем HTTPS-only ограничения
SECURE_HSTS_SECONDS = 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Локальный доступ по любому хосту (localhost / 127.0.0.1 / IP в сети)
ALLOWED_HOSTS = ['*']

# Доступ из локальной сети с других машин: разрешаем CORS отовсюду и
# доверяем CSRF для http/https (нужно для входа в админку по IP).
# Для self-hosted демо в доверенной сети это безопасно.
CORS_ALLOW_ALL_ORIGINS = True
CSRF_TRUSTED_ORIGINS = ['http://*', 'https://*']
