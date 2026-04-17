from django.db import models
from django.conf import settings

class ChatMessage(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name='Отправитель'
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_messages',
        verbose_name='Получатель',
        null=True,
        blank=True
    )
    text = models.TextField(verbose_name='Текст сообщения')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')

    class Meta:
        ordering = ['created_at']
        verbose_name = 'Сообщение чата'
        verbose_name_plural = 'Сообщения чата'

    def __str__(self):
        return f'{self.user.username}: {self.text[:50]}'
