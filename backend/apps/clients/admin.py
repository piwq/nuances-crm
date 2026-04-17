from django.contrib import admin
from .models import Client, ContactPerson


class ContactPersonInline(admin.TabularInline):
    model = ContactPerson
    extra = 0


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'client_type', 'email', 'phone', 'created_at']
    list_filter = ['client_type']
    search_fields = ['first_name', 'last_name', 'company_name', 'email']
    inlines = [ContactPersonInline]
