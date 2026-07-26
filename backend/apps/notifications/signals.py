from django.db.models.signals import post_save, pre_save, m2m_changed
from django.dispatch import receiver

from apps.tasks.models import Task
from apps.cases.models import Case
from apps.documents.models import Document
from apps.chat.models import ChatMessage
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


@receiver(pre_save, sender=Case)
def stash_old_case_fields(sender, instance, **kwargs):
    """Запоминаем старые значения, чтобы в post_save понять, что изменилось."""
    if instance.pk:
        old = Case.objects.filter(pk=instance.pk).values('lead_lawyer_id', 'key_deadline').first()
    else:
        old = None
    instance._old_lead_id = old['lead_lawyer_id'] if old else None
    instance._old_deadline = old['key_deadline'] if old else None


@receiver(post_save, sender=Case)
def notify_case_changes(sender, instance, created, **kwargs):
    skip_uid = getattr(instance, '_notify_skip_user', None)
    # новый ответственный юрист (кроме случая «сам себя при создании»)
    if instance.lead_lawyer_id and instance.lead_lawyer_id != skip_uid and \
            instance.lead_lawyer_id != getattr(instance, '_old_lead_id', None):
        create_notification(
            user=instance.lead_lawyer,
            title=f'Вы ответственный по делу: {instance.title}',
            body=f'Дело {instance.case_number}',
            link=f'/cases/{instance.uuid}',
            key=f'case_{instance.id}_lead_{instance.lead_lawyer_id}',
        )
    # перенос процессуального срока (только изменение существующего дела)
    if not created and instance.key_deadline and \
            instance.key_deadline != getattr(instance, '_old_deadline', None):
        note = f' — {instance.key_deadline_note}' if instance.key_deadline_note else ''
        recipients = set(instance.assigned_lawyers.all())
        if instance.lead_lawyer:
            recipients.add(instance.lead_lawyer)
        for user in recipients:
            create_notification(
                user=user,
                title=f'Изменён процессуальный срок: {instance.title}',
                body=f'Новый срок: {instance.key_deadline}{note}',
                link=f'/cases/{instance.uuid}',
                key=f'case_{instance.id}_deadline_{instance.key_deadline}_user_{user.id}',
            )


@receiver(m2m_changed, sender=Case.assigned_lawyers.through)
def notify_case_assignment(sender, instance, action, pk_set, **kwargs):
    if action != 'post_add' or not pk_set:
        return
    from apps.accounts.models import CustomUser
    skip_uid = getattr(instance, '_notify_skip_user', None)
    for user in CustomUser.objects.filter(pk__in=pk_set):
        if user.pk == skip_uid:
            continue
        create_notification(
            user=user,
            title=f'Вы назначены на дело: {instance.title}',
            body=f'Дело {instance.case_number}',
            link=f'/cases/{instance.uuid}',
            key=f'case_{instance.id}_assigned_{user.id}',
        )


@receiver(post_save, sender=Document)
def notify_new_document(sender, instance, created, **kwargs):
    if not created or not instance.case_id:
        return
    case = instance.case
    recipients = set(case.assigned_lawyers.all())
    if case.lead_lawyer:
        recipients.add(case.lead_lawyer)
    recipients.discard(instance.uploaded_by)
    for user in recipients:
        create_notification(
            user=user,
            title=f'Новый документ по делу: {case.title}',
            body=instance.title,
            link=f'/cases/{case.uuid}',
            key=f'doc_{instance.uuid}_user_{user.id}',
        )


@receiver(post_save, sender=ChatMessage)
def notify_chat_message(sender, instance, created, **kwargs):
    if not created or not instance.recipient_id:
        return
    sender_name = instance.user.get_full_name() or instance.user.username
    text = instance.text if len(instance.text) <= 80 else instance.text[:77] + '…'
    create_notification(
        user=instance.recipient,
        title=f'Сообщение от {sender_name}',
        body=text,
        link='/chat',
        key=f'chat_msg_{instance.id}',
    )
