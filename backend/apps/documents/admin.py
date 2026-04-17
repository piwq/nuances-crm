from django.contrib import admin
from .models import Document


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['title', 'document_type', 'case', 'uploaded_by', 'uploaded_at']
    list_filter = ['document_type']
    search_fields = ['title', 'case__title']
