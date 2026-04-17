import django_filters
from .models import Case


class CaseFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(method='filter_search')
    assigned_lawyer = django_filters.NumberFilter(field_name='assigned_lawyers__id')

    class Meta:
        model = Case
        fields = ['status', 'category', 'client']

    def filter_search(self, queryset, name, value):
        from django.db.models import Q
        return queryset.filter(
            Q(title__icontains=value) |
            Q(case_number__icontains=value) |
            Q(court_case_number__icontains=value) |
            Q(client__last_name__icontains=value) |
            Q(client__company_name__icontains=value)
        ).distinct()
