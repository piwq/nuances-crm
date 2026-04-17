import uuid
import mimetypes
from django.db import models
from django.conf import settings


def case_document_upload_path(instance, filename):
    return f'documents/case_{instance.case_id}/{filename}'


class Document(models.Model):
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, db_index=True)
    TYPE_CONTRACT = 'contract'
    TYPE_POA = 'power_of_attorney'
    TYPE_COURT_FILING = 'court_filing'
    TYPE_EVIDENCE = 'evidence'
    TYPE_CORRESPONDENCE = 'correspondence'
    TYPE_OTHER = 'other'
    TYPE_CHOICES = [
        (TYPE_CONTRACT, 'Договор'),
        (TYPE_POA, 'Доверенность'),
        (TYPE_COURT_FILING, 'Судебное обращение'),
        (TYPE_EVIDENCE, 'Доказательство'),
        (TYPE_CORRESPONDENCE, 'Переписка'),
        (TYPE_OTHER, 'Прочее'),
    ]

    case = models.ForeignKey(
        'cases.Case',
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Дело',
    )
    title = models.CharField(max_length=255, verbose_name='Название')
    document_type = models.CharField(max_length=30, choices=TYPE_CHOICES, verbose_name='Тип')
    file = models.FileField(upload_to=case_document_upload_path, verbose_name='Файл')
    file_size = models.PositiveIntegerField(null=True, blank=True, verbose_name='Размер (байт)')
    mime_type = models.CharField(max_length=100, blank=True, verbose_name='MIME тип')
    description = models.TextField(blank=True, verbose_name='Описание')

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents',
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name = 'Документ'
        verbose_name_plural = 'Документы'

    def __str__(self):
        return f'{self.title} ({self.get_document_type_display()})'

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, 'size'):
            self.file_size = self.file.size
            self.mime_type = mimetypes.guess_type(self.file.name)[0] or ''
        super().save(*args, **kwargs)
