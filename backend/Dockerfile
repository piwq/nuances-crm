FROM python:3.12-slim

WORKDIR /app

# только runtime-библиотеки WeasyPrint; компиляторы не нужны (все пакеты — wheel'ы)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --uid 1000 app

COPY requirements/ ./requirements/
RUN pip install --no-cache-dir -r requirements/production.txt -c requirements/constraints.txt

COPY --chown=app:app . .

RUN mkdir -p /app/media /app/staticfiles && chown app:app /app/media /app/staticfiles

USER app

RUN DJANGO_SETTINGS_MODULE=config.settings.production SECRET_KEY=dummy python manage.py collectstatic --noinput

# логи долгоживущих процессов (бот, daphne) не должны застревать в буфере
ENV PYTHONUNBUFFERED=1

EXPOSE 8000
