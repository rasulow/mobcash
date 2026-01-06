from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import TransactionViewSet, WalletTransferViewSet, WalletViewSet

router = DefaultRouter()
router.register(r"wallets", WalletViewSet, basename="wallets")
router.register(r"transactions", TransactionViewSet, basename="transactions")
router.register(r"wallet-transfers", WalletTransferViewSet, basename="wallet-transfers")

urlpatterns = [
    path("", include(router.urls)),
]


