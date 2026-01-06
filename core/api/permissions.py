from rest_framework.permissions import BasePermission


class IsMainCashier(BasePermission):
    message = "Требуется роль main_cashier."

    def has_permission(self, request, view) -> bool:
        u = getattr(request, "user", None)
        return bool(u and u.is_authenticated and u.groups.filter(name="main_cashier").exists())


class IsSuperAdmin(BasePermission):
    message = "Требуется роль superadmin."

    def has_permission(self, request, view) -> bool:
        u = getattr(request, "user", None)
        return bool(u and u.is_authenticated and u.is_superuser)


