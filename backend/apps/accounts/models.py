from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    ROLE_ADMIN = 'admin'
    ROLE_LAWYER = 'lawyer'
    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Администратор'),
        (ROLE_LAWYER, 'Юрист'),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_LAWYER, verbose_name='Роль')
    phone = models.CharField(max_length=30, blank=True, verbose_name='Телефон')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='Аватар')

    class Meta:
        db_table = 'accounts_user'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return f'{self.get_full_name() or self.username} ({self.get_role_display()})'

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN

    @property
    def is_lawyer(self):
        return self.role == self.ROLE_LAWYER
