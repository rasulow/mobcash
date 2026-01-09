from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .integration_views import IntegrationViewSet
from .views import SPMTransactionViewSet, TransactionViewSet, WalletTransferViewSet, WalletViewSet

router = DefaultRouter()
router.register(r"wallets", WalletViewSet, basename="wallets")
router.register(r"transactions", TransactionViewSet, basename="transactions")
router.register(r"wallet-transfers", WalletTransferViewSet, basename="wallet-transfers")
router.register(r"spm", SPMTransactionViewSet, basename="spm")
router.register(r"integration", IntegrationViewSet, basename="integration")

urlpatterns = [
    path("", include(router.urls)),
]


