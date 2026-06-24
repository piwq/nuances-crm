from django.contrib import admin
from .models import Document, DocumentTemplate


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'document_type', 'case', 'uploaded_by', 'uploaded_at']
    list_filter = ['document_type']
    search_fields = ['title', 'case__title']


@admin.register(DocumentTemplate)
class DocumentTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'document_type', 'created_at']
    list_filter = ['document_type']
    search_fields = ['name']
