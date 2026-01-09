from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import transaction as db_transaction
from django.db.models import F
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.models import Transaction, Wallet, WalletTransfer

from .cashier_serializers import CashierAccountCreateSerializer
from .admin_serializers import (
    AdminGroupSerializer,
    AdminTransactionSerializer,
    AdminUserSerializer,
    AdminWalletSerializer,
    AdminWalletTransferCreateSerializer,
    AdminWalletTransferSerializer,
    WalletCreateSerializer,
    WalletIncreaseBalanceSerializer,
)
from .permissions import IsSuperAdmin, IsSuperAdminOrMainCashier

User = get_user_model()


class AdminUserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.select_related("wallet").prefetch_related("groups").all().order_by("id")
    serializer_class = AdminUserSerializer
    permission_classes = [IsSuperAdmin]

    def get_permissions(self):
        """
        superadmin: full access
        main_cashier: can list/retrieve users and create cashier accounts only
        """
        if getattr(self.request, "user", None) and self.request.user.is_superuser:
            return [IsSuperAdmin()]

        if self.action in ["list", "retrieve", "create"]:
            return [IsSuperAdminOrMainCashier()]

        # update / partial_update / destroy remain superadmin-only
        return [IsSuperAdmin()]

    def get_serializer_class(self):
        # main_cashier should only be able to create cashier accounts (no group/flags control).
        if self.action == "create" and not self.request.user.is_superuser:
            return CashierAccountCreateSerializer
        return AdminUserSerializer


class AdminGroupViewSet(viewsets.ModelViewSet):
    queryset = Group.objects.all().order_by("name")
    serializer_class = AdminGroupSerializer
    permission_classes = [IsSuperAdmin]


class AdminWalletViewSet(viewsets.ModelViewSet):
    queryset = Wallet.objects.select_related("user").all().order_by("user__username")
    serializer_class = AdminWalletSerializer
    permission_classes = [IsSuperAdmin]
    http_method_names = ["get", "post", "patch", "put", "head", "options"]

    def get_permissions(self):
        """
        superadmin: full access
        main_cashier: can create wallets for cashier users only
        """
        if self.action == "create":
            return [IsSuperAdminOrMainCashier()]
        return [IsSuperAdmin()]

    def get_serializer_class(self):
        if self.action == "create":
            return WalletCreateSerializer
        return AdminWalletSerializer

    @swagger_auto_schema(
        operation_description="Create a wallet for a user. Superadmin can create for any user, main_cashier can only create for cashier users.",
        request_body=WalletCreateSerializer,
        responses={201: AdminWalletSerializer, 400: "Bad Request", 403: "Forbidden", 404: "User not found"}
    )
    def create(self, request, *args, **kwargs):
        """
        Superadmin: create a wallet for any user.
        Main cashier: create a wallet for cashier users only.
        """
        ser = WalletCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        user_id = ser.validated_data["user_id"]
        currency = ser.validated_data.get("currency", "TMT")
        balance = ser.validated_data.get("balance", Decimal("0"))

        user = User.objects.filter(pk=user_id).first()
        if not user:
            return Response({"detail": "Пользователь не найден."}, status=status.HTTP_404_NOT_FOUND)

        # main_cashier can only create wallets for cashier users
        if not request.user.is_superuser:
            if not user.groups.filter(name="cashier").exists():
                return Response(
                    {"detail": "Можно создавать кошельки только для пользователей с ролью cashier."},
                    status=status.HTTP_403_FORBIDDEN,
                )
            if user.is_superuser or user.groups.filter(name="main_cashier").exists():
                return Response(
                    {"detail": "Нельзя создавать кошельки для superadmin или main_cashier."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        if Wallet.objects.filter(user=user).exists():
            return Response(
                {"detail": "У этого пользователя уже есть кошелёк."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet = Wallet.objects.create(user=user, currency=currency, balance=balance)
        return Response(AdminWalletSerializer(wallet).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        return Response(AdminWalletSerializer(wallet).data)

    @action(detail=False, methods=["post"], url_path="me/increase-balance")
    def increase_my_balance(self, request):
        """
        Superadmin only: increase own wallet balance by specified amount.
        """
        ser = WalletIncreaseBalanceSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        amount: Decimal = ser.validated_data["amount"]

        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        with db_transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
            Wallet.objects.filter(pk=wallet.pk).update(balance=F("balance") + amount)
            wallet.refresh_from_db(fields=["balance", "currency"])

        return Response(AdminWalletSerializer(wallet).data, status=status.HTTP_200_OK)


class AdminTransactionViewSet(mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    queryset = Transaction.objects.select_related("wallet", "wallet__user").all().order_by("-created_at")
    serializer_class = AdminTransactionSerializer
    permission_classes = [IsSuperAdmin]


class AdminWalletTransferViewSet(
    mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    queryset = WalletTransfer.objects.select_related(
        "from_wallet",
        "from_wallet__user",
        "to_wallet",
        "to_wallet__user",
    ).all().order_by("-created_at")
    serializer_class = AdminWalletTransferSerializer
    permission_classes = [IsSuperAdmin]

    def get_serializer_class(self):
        if self.action == "create":
            return AdminWalletTransferCreateSerializer
        return AdminWalletTransferSerializer

    def create(self, request, *args, **kwargs):
        """
        Superadmin only: deposit to or withdraw from main_cashier/cashier wallet.
        - deposit: decreases superadmin balance, increases target balance
        - withdraw: increases superadmin balance, decreases target balance
        """
        ser = AdminWalletTransferCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        to_user_id = ser.validated_data["to_user_id"]
        amount: Decimal = ser.validated_data["amount"]
        transaction_type = ser.validated_data["transaction_type"]

        from_wallet, _ = Wallet.objects.get_or_create(user=request.user)

        to_user = User.objects.filter(pk=to_user_id).first()
        if not to_user:
            return Response({"detail": "Пользователь не найден."}, status=status.HTTP_404_NOT_FOUND)
        
        # Allow transfers to main_cashier or cashier
        is_main_cashier = to_user.groups.filter(name="main_cashier").exists()
        is_cashier = to_user.groups.filter(name="cashier").exists()
        
        if not (is_main_cashier or is_cashier):
            return Response(
                {"detail": "Можно переводить только пользователям с ролью main_cashier или cashier."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if to_user.is_superuser:
            return Response(
                {"detail": "Нельзя переводить superadmin через этот endpoint."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if to_user.id == request.user.id:
            return Response({"detail": "Нельзя переводить самому себе."}, status=status.HTTP_400_BAD_REQUEST)

        to_wallet, _ = Wallet.objects.get_or_create(user=to_user)

        with db_transaction.atomic():
            from_wallet = Wallet.objects.select_for_update().get(pk=from_wallet.pk)
            to_wallet = Wallet.objects.select_for_update().get(pk=to_wallet.pk)
            
            if transaction_type == "deposit":
                # Deposit: superadmin sends money to target user
                if from_wallet.balance < amount:
                    return Response(
                        {"detail": f"Недостаточно средств: баланс {from_wallet.balance}, нужно {amount}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                Wallet.objects.filter(pk=from_wallet.pk).update(balance=F("balance") - amount)
                Wallet.objects.filter(pk=to_wallet.pk).update(balance=F("balance") + amount)
            else:  # withdraw
                # Withdraw: superadmin takes money from target user
                if to_wallet.balance < amount:
                    return Response(
                        {"detail": f"Недостаточно средств у пользователя: баланс {to_wallet.balance}, нужно {amount}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                Wallet.objects.filter(pk=from_wallet.pk).update(balance=F("balance") + amount)
                Wallet.objects.filter(pk=to_wallet.pk).update(balance=F("balance") - amount)
            
            wt = WalletTransfer.objects.create(from_wallet=from_wallet, to_wallet=to_wallet, amount=amount)

        return Response(AdminWalletTransferSerializer(wt).data, status=status.HTTP_201_CREATED)


