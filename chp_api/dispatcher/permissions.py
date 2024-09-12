from rest_framework import permissions


class CustomQueryPostPermission(permissions.BasePermission):
    """
    Allows the query POST endpoint to work without any permissions.
    """

    def has_permission(self, request, view):
        return True
