from django.http import FileResponse
import os


def serve_file_response(file_field, filename=None):
    """Return a FileResponse for download with proper Content-Disposition."""
    file_handle = file_field.open('rb')
    name = filename or os.path.basename(file_field.name)
    response = FileResponse(file_handle, as_attachment=True, filename=name)
    return response


def log_activity(user, action, resource_type, resource_uuid=None, description=""):
    """Logs an activity to the ActivityLog model."""
    from apps.audit.models import ActivityLog
    ActivityLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action=action,
        resource_type=resource_type,
        resource_uuid=resource_uuid,
        description=description
    )
