import uuid
from django.db import models
from django.conf import settings


class Client(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    TYPE_INDIVIDUAL = 'individual'
    TYPE_LEGAL = 'legal_entity'
    TYPE_CHOICES = [
        (TYPE_INDIVIDUAL, 'Физическое лицо'),
        (TYPE_LEGAL, 'Юридическое лицо'),
    ]

    client_type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name='Тип клиента')

    # Физическое лицо
    first_name = models.CharField(max_length=100, blank=True, verbose_name='Имя')
    last_name = models.CharField(max_length=100, blank=True, verbose_name='Фамилия')
    middle_name = models.CharField(max_length=100, blank=True, verbose_name='Отчество')
    date_of_birth = models.DateField(null=True, blank=True, verbose_name='Дата рождения')
    passport_number = models.CharField(max_length=50, blank=True, verbose_name='Паспорт')
    tax_id = models.CharField(max_length=50, blank=True, verbose_name='ИНН')

    # Юридическое лицо
    company_name = models.CharField(max_length=255, blank=True, verbose_name='Название компании')
    registration_number = models.CharField(max_length=100, blank=True, verbose_name='ОГРН')
    legal_address = models.TextField(blank=True, verbose_name='Юридический адрес')

    # Общие
    email = models.EmailField(blank=True, verbose_name='Email')
    phone = models.CharField(max_length=30, blank=True, verbose_name='Телефон')
    address = models.TextField(blank=True, verbose_name='Адрес')
    notes = models.TextField(blank=True, verbose_name='Заметки')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_clients',
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Клиент'
        verbose_name_plural = 'Клиенты'

    def __str__(self):
        if self.client_type == self.TYPE_INDIVIDUAL:
            return f'{self.last_name} {self.first_name} {self.middle_name}'.strip()
        return self.company_name

    @property
    def display_name(self):
        return str(self)


class ContactPerson(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='contact_persons')
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    middle_name = models.CharField(max_length=100, blank=True, verbose_name='Отчество')
    position = models.CharField(max_length=150, blank=True, verbose_name='Должность')
    phone = models.CharField(max_length=30, blank=True, verbose_name='Телефон')
    email = models.EmailField(blank=True, verbose_name='Email')
    is_primary = models.BooleanField(default=False, verbose_name='Основной')

    class Meta:
        ordering = ['-is_primary', 'last_name']
        verbose_name = 'Контактное лицо'
        verbose_name_plural = 'Контактные лица'

    def __str__(self):
        return f'{self.last_name} {self.first_name} ({self.client})'
