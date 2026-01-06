from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .admin_views import (
    AdminGroupViewSet,
    AdminTransactionViewSet,
    AdminUserViewSet,
    AdminWalletTransferViewSet,
    AdminWalletViewSet,
)

router = DefaultRouter()
router.register(r"users", AdminUserViewSet, basename="admin-users")
router.register(r"groups", AdminGroupViewSet, basename="admin-groups")
router.register(r"wallets", AdminWalletViewSet, basename="admin-wallets")
router.register(r"transactions", AdminTransactionViewSet, basename="admin-transactions")
router.register(r"wallet-transfers", AdminWalletTransferViewSet, basename="admin-wallet-transfers")

urlpatterns = [
    path("", include(router.urls)),
]


