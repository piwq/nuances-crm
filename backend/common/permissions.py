from rest_framework.permissions import BasePermission


class IsAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_admin)


class IsAdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in ('GET', 'HEAD', 'OPTIONS'):
            return True
        return request.user.is_admin


class IsLawyerAssignedToCase(BasePermission):
    """For case-specific views: allow admin or assigned lawyer."""

    def has_object_permission(self, request, view, obj):
        if request.user.is_admin:
            return True
        # obj is a Case instance
        case = obj
        return case.assigned_lawyers.filter(pk=request.user.pk).exists() or \
               (case.lead_lawyer_id == request.user.pk)
