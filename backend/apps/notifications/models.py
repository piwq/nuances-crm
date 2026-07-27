from django.db import models
from django.conf import settings


class Notification(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications'
    )
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    # unique key prevents duplicate reminders (e.g. "task_42_due_1d")
    key = models.CharField(max_length=200, blank=True, default='', db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read']),
            models.Index(fields=['-created_at']),
        ]
        constraints = [
            # дедупликация напоминаний была только через filter().exists() —
            # два параллельных прогона планировщика могли создать дубль
            models.UniqueConstraint(
                fields=['user', 'key'],
                condition=~models.Q(key=''),
                name='uniq_notification_key_per_user',
            ),
        ]

    def __str__(self):
        return f'{self.user} — {self.title}'
