from django.db import models
from django.conf import settings

class ActivityLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=255) # e.g. "CREATE", "UPDATE", "DELETE", "DOWNLOAD"
    resource_type = models.CharField(max_length=100) # e.g. "Case", "Document"
    resource_uuid = models.UUIDField(null=True, blank=True)
    description = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Лог активности'
        verbose_name_plural = 'Логи активности'

    def __str__(self):
        return f"{self.timestamp} - {self.user} - {self.action} on {self.resource_type}"
