from django.contrib import admin
from .models import TimeEntry, Invoice, InvoiceItem


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ['date', 'case', 'lawyer', 'hours', 'hourly_rate', 'is_billable', 'invoice']
    list_filter = ['is_billable', 'lawyer']
    search_fields = ['case__title', 'description']


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0
    readonly_fields = ['amount']


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'client', 'case', 'status', 'total', 'due_date']
    list_filter = ['status']
    inlines = [InvoiceItemInline]
    readonly_fields = ['invoice_number', 'tax_amount', 'total', 'created_at']
