from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.tasks.models import Task
from .models import Notification


@receiver(post_save, sender=Task)
def notify_task_assignee(sender, instance, created, **kwargs):
    if not instance.assigned_to:
        return
    if created:
        title = f'Новая задача: {instance.title}'
        body = f'Вам назначена задача с приоритетом «{instance.get_priority_display()}»'
        if instance.due_date:
            body += f', срок: {instance.due_date}'
        link = f'/tasks'
        if instance.case_id:
            link = f'/cases/{instance.case.uuid}'
        Notification.objects.create(
            user=instance.assigned_to,
            title=title,
            body=body,
            link=link,
        )
