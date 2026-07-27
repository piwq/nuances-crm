"""Боевые настройки.

Рассчитаны на доступ по HTTP внутри доверенной локальной сети (текущий режим)
с возможностью включить HTTPS одной переменной, когда появится домен или VPN:
    USE_HTTPS=True  →  secure-куки, HSTS, редирект на https.
"""
from .base import *  # noqa: F403

DEBUG = False

# SECRET_KEY обязателен: без него base.py молча подставит публичный дефолт
if SECRET_KEY == 'dev-secret-key-change-in-production':  # noqa: F405
    raise ImproperlyConfigured(  # noqa: F405
        'SECRET_KEY не задан в окружении — прод не должен запускаться '
        'с ключом по умолчанию.'
    )

# ── Заголовки безопасности, не требующие TLS ────────────────────────────
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'

# ── HTTPS-механизмы: включаются вместе с доменом/VPN ────────────────────
USE_HTTPS = config('USE_HTTPS', default=False, cast=bool)  # noqa: F405

SESSION_COOKIE_SECURE = USE_HTTPS
CSRF_COOKIE_SECURE = USE_HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') if USE_HTTPS else None

# Редирект на HTTPS — отдельно от USE_HTTPS: пока в системе два входа
# (https через VPN и http из локальной сети), принудительный редирект уводил
# бы LAN-запросы на https://<IP>, где сертификата нет и быть не может.
# Включать, когда локальный http-доступ станет не нужен.
SECURE_SSL_REDIRECT = config('FORCE_SSL_REDIRECT', default=False, cast=bool)  # noqa: F405
# HSTS ставится только при рабочем TLS: включить его на http — значит
# заблокировать себе доступ к сайту до истечения срока в браузере
SECURE_HSTS_SECONDS = 31536000 if USE_HTTPS else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = USE_HTTPS
SECURE_HSTS_PRELOAD = USE_HTTPS

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# ── Документация API: в проде только для админов ────────────────────────
SPECTACULAR_SETTINGS = {  # noqa: F405
    **SPECTACULAR_SETTINGS,  # noqa: F405
    'SERVE_PERMISSIONS': ['rest_framework.permissions.IsAdminUser'],
}

# Фронтенд и API живут на одном origin через nginx — CORS не нужен
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = config(  # noqa: F405
    'CORS_ALLOWED_ORIGINS', default='',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()],
)
CSRF_TRUSTED_ORIGINS = config(  # noqa: F405
    'CSRF_TRUSTED_ORIGINS', default='',
    cast=lambda v: [s.strip() for s in v.split(',') if s.strip()],
)
