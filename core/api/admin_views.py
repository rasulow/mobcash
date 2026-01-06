from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from rest_framework import mixins, viewsets

from core.models import Transaction, Wallet, WalletTransfer

from .admin_serializers import (
    AdminGroupSerializer,
    AdminTransactionSerializer,
    AdminUserSerializer,
    AdminWalletSerializer,
    AdminWalletTransferSerializer,
)
from .permissions import IsSuperAdmin

User = get_user_model()


class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all().order_by("id")
    serializer_class = AdminUserSerializer
    permission_classes = [IsSuperAdmin]


class AdminGroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all().order_by("name")
    serializer_class = AdminGroupSerializer
    permission_classes = [IsSuperAdmin]


class AdminWalletViewSet(viewsets.ModelViewSet):
    queryset = Wallet.objects.select_related("user").all().order_by("user__username")
    serializer_class = AdminWalletSerializer
    permission_classes = [IsSuperAdmin]
    http_method_names = ["get", "patch", "put", "head", "options"]


class AdminTransactionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Transaction.objects.select_related("wallet", "wallet__user").all().order_by("-created_at")
    serializer_class = AdminTransactionSerializer
    permission_classes = [IsSuperAdmin]


class AdminWalletTransferViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = WalletTransfer.objects.select_related(
        "from_wallet",
        "from_wallet__user",
        "to_wallet",
        "to_wallet__user",
    ).all().order_by("-created_at")
    serializer_class = AdminWalletTransferSerializer
    permission_classes = [IsSuperAdmin]


