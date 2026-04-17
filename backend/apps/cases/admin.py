from django.contrib import admin
from .models import Case


@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ['case_number', 'title', 'client', 'status', 'category', 'lead_lawyer', 'opened_at']
    list_filter = ['status', 'category']
    search_fields = ['title', 'case_number', 'client__last_name', 'client__company_name']
    filter_horizontal = ['assigned_lawyers']
    readonly_fields = ['case_number', 'created_at', 'updated_at']
