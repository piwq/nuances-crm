from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.tasks.models import Task
from .utils import create_notification


@receiver(post_save, sender=Task)
def notify_task_assignee(sender, instance, created, **kwargs):
    if not instance.assigned_to or not created:
        return
    body = f'Приоритет: {instance.get_priority_display()}'
    if instance.due_date:
        body += f', срок: {instance.due_date}'
    link = f'/cases/{instance.case.uuid}' if instance.case_id else '/tasks'
    create_notification(
        user=instance.assigned_to,
        title=f'Новая задача: {instance.title}',
        body=body,
        link=link,
        key=f'task_created_{instance.id}',
    )
