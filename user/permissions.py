from rest_framework.permissions import BasePermission

class IsAitusaOrAdminReadOnly(BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and request.user.is_authenticated and (
                request.user.role in ['aitusa', 'admin'] and request.method in ['GET', 'HEAD']
            )
        )
