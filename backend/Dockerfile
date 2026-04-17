FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements/ ./requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

COPY . .

RUN DJANGO_SETTINGS_MODULE=config.settings.production SECRET_KEY=dummy python manage.py collectstatic --noinput

EXPOSE 8000
