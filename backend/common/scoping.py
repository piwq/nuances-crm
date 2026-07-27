"""Скоупинг данных по роли: юрист видит только свои дела и всё, что к ним привязано."""
from django.db.models import Q


def scope_cases(qs, user):
    """Ограничить queryset дел: юрист — только назначенные ему или ведомые им."""
    if user.is_scoped:
        qs = qs.filter(Q(assigned_lawyers=user) | Q(lead_lawyer=user)).distinct()
    return qs


def scope_by_case(qs, user, case_field='case'):
    """То же для моделей с FK на дело (документы, счета, заметки и т.п.)."""
    if user.is_scoped:
        qs = qs.filter(
            Q(**{f'{case_field}__assigned_lawyers': user}) |
            Q(**{f'{case_field}__lead_lawyer': user})
        ).distinct()
    return qs


def user_can_access_case(user, case):
    """Object-level проверка доступа к конкретному делу."""
    if not user.is_scoped:
        return True
    return (
        case.lead_lawyer_id == user.pk or
        case.assigned_lawyers.filter(pk=user.pk).exists()
    )
