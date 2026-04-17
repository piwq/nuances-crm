import django_filters
from .models import Client


class ClientFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='filter_search')

    class Meta:
        model = Client
        fields = ['client_type']

    def filter_search(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(first_name__icontains=value) |
            Q(last_name__icontains=value) |
            Q(middle_name__icontains=value) |
            Q(company_name__icontains=value) |
            Q(email__icontains=value) |
            Q(phone__icontains=value)
        )
