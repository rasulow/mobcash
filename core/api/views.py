from datetime import timedelta
from decimal import Decimal

import secrets
import uuid

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction as db_transaction
from django.db.models import F
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from core.external_api import ExternalApiError, fetch_yildiztop_users_by_referral_token, post_yildiztop_update_balance
from core.models import SPMWithdrawConfirmation, Transaction, Wallet, WalletTransfer
from core.spm_api import get_spm_client, SPMApiError

from .permissions import IsMainCashier, IsSuperAdminOrMainCashierOrCashier
from .serializers import (
    SPMDepositStatusResponseSerializer,
    SPMDepositStatusSerializer,
    SPMGetUserByUserIdSerializer,
    SPMGetUserByUserNameSerializer,
    SPMRegisterUserResponseSerializer,
    SPMRegisterUserSerializer,
    SPMSessionResponseSerializer,
    SPMSessionSerializer,
    SPMTransactionResponseSerializer,
    SPMTransactionSerializer,
    SPMUserResponseSerializer,
    SPMWithdrawSendCodeSerializer,
    SPMWithdrawSerializer,
    TransactionCreateSerializer,
    TransactionSerializer,
    WalletSerializer,
    WalletTransferCreateSerializer,
    WalletTransferSerializer,
)

User = get_user_model()


class WalletViewSet(viewsets.GenericViewSet):
    queryset = Wallet.objects.select_related("user").all()
    serializer_class = WalletSerializer

    def list(self, request, *args, **kwargs):
        if not (request.user.is_superuser or request.user.groups.filter(name="main_cashier").exists()):
            return Response({"detail": "Недостаточно прав."}, status=status.HTTP_403_FORBIDDEN)
        qs = self.get_queryset().order_by("user__username")
        return Response(WalletSerializer(qs, many=True).data)

    @action(detail=False, methods=["get"])
    def me(self, request):
        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        return Response(WalletSerializer(wallet).data)


class TransactionViewSet(viewsets.GenericViewSet):
    queryset = Transaction.objects.select_related("wallet", "wallet__user").all()
    serializer_class = TransactionSerializer

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        elevated = request.user.is_superuser or request.user.groups.filter(name="main_cashier").exists()
        if not elevated:
            qs = qs.filter(wallet__user=request.user)
        else:
            user_id = request.query_params.get("user_id")
            if user_id:
                qs = qs.filter(wallet__user_id=user_id)
        qs = qs.order_by("-created_at")
        return Response(TransactionSerializer(qs[:200], many=True).data)

    def retrieve(self, request, pk=None):
        obj = self.get_queryset().filter(pk=pk).first()
        if not obj:
            return Response({"detail": "Не найдено."}, status=status.HTTP_404_NOT_FOUND)
        elevated = request.user.is_superuser or request.user.groups.filter(name="main_cashier").exists()
        if not elevated and obj.wallet.user_id != request.user.id:
            return Response({"detail": "Недостаточно прав."}, status=status.HTTP_403_FORBIDDEN)
        return Response(TransactionSerializer(obj).data)

    def create(self, request, *args, **kwargs):
        data_ser = TransactionCreateSerializer(data=request.data)
        data_ser.is_valid(raise_exception=True)
        referral_token = data_ser.validated_data["referral_token"]
        amount: Decimal = data_ser.validated_data["amount"]
        tx_type: str = data_ser.validated_data["type"]
        note: str = data_ser.validated_data.get("note", "")

        wallet, _ = Wallet.objects.get_or_create(user=request.user)

        # If DEPOSIT spends our wallet, enforce funds before calling external API.
        if tx_type == Transaction.Type.DEPOSIT:
            with db_transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
                if wallet.balance < amount:
                    return Response(
                        {"detail": f"Недостаточно средств: баланс {wallet.balance}, нужно {amount}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                # External update: signed amount (+deposit, -withdraw)
                signed_amount = amount if tx_type == Transaction.Type.DEPOSIT else -amount
                try:
                    post_yildiztop_update_balance(referral_token, signed_amount)
                except ExternalApiError as e:
                    return Response({"detail": f"Ошибка внешнего API: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

                # Save transaction
                tx = Transaction.objects.create(
                    wallet=wallet,
                    type=tx_type,
                    amount=amount,
                    note=note,
                    external_referral_token=referral_token,
                    external_sync_status=Transaction.ExternalSyncStatus.SYNCED,
                    external_sync_error="",
                )

                # Enrich with external user if possible (best-effort)
                try:
                    users = fetch_yildiztop_users_by_referral_token(referral_token)
                    u = users[0] if users else None
                    if u:
                        tx.external_user_id = u.id
                        tx.external_user_name = u.name
                        tx.external_user_email = u.email or ""
                        tx.save(update_fields=["external_user_id", "external_user_name", "external_user_email"])
                except ExternalApiError:
                    pass

                # Spend our wallet for DEPOSIT only (per current business rule)
                Wallet.objects.filter(pk=wallet.pk).update(balance=F("balance") - amount)
                return Response(TransactionSerializer(tx).data, status=status.HTTP_201_CREATED)

        # WITHDRAW path: does NOT spend our wallet (per current business rule)
        signed_amount = amount if tx_type == Transaction.Type.DEPOSIT else -amount
        try:
            post_yildiztop_update_balance(referral_token, signed_amount)
        except ExternalApiError as e:
            return Response({"detail": f"Ошибка внешнего API: {e}"}, status=status.HTTP_502_BAD_GATEWAY)

        tx = Transaction.objects.create(
            wallet=wallet,
            type=tx_type,
            amount=amount,
            note=note,
            external_referral_token=referral_token,
            external_sync_status=Transaction.ExternalSyncStatus.SYNCED,
            external_sync_error="",
        )
        try:
            users = fetch_yildiztop_users_by_referral_token(referral_token)
            u = users[0] if users else None
            if u:
                tx.external_user_id = u.id
                tx.external_user_name = u.name
                tx.external_user_email = u.email or ""
                tx.save(update_fields=["external_user_id", "external_user_name", "external_user_email"])
        except ExternalApiError:
            pass

        return Response(TransactionSerializer(tx).data, status=status.HTTP_201_CREATED)


class WalletTransferViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    queryset = WalletTransfer.objects.select_related(
        "from_wallet",
        "from_wallet__user",
        "to_wallet",
        "to_wallet__user",
    ).all()
    serializer_class = WalletTransferSerializer
    permission_classes = [IsMainCashier]

    def get_serializer_class(self):
        if self.action == "create":
            return WalletTransferCreateSerializer
        return WalletTransferSerializer

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                "transaction_type",
                openapi.IN_QUERY,
                description="Filter by transaction type",
                type=openapi.TYPE_STRING,
                enum=["deposit", "withdraw"],
            )
        ]
    )
    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        
        # Filter by transaction_type if provided
        transaction_type = request.query_params.get('transaction_type')
        if transaction_type in ['deposit', 'withdraw']:
            qs = qs.filter(transaction_type=transaction_type)
        
        return Response(WalletTransferSerializer(qs[:200], many=True).data)

    def create(self, request, *args, **kwargs):
        ser = WalletTransferCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        to_user_id = ser.validated_data["to_user_id"]
        amount: Decimal = ser.validated_data["amount"]
        transaction_type = ser.validated_data["transaction_type"]

        from_wallet, _ = Wallet.objects.get_or_create(user=request.user)
        to_user = User.objects.filter(pk=to_user_id).first()
        if not to_user:
            return Response({"detail": "Пользователь не найден."}, status=status.HTTP_404_NOT_FOUND)
        if to_user.id == request.user.id:
            return Response({"detail": "Нельзя переводить самому себе."}, status=status.HTTP_400_BAD_REQUEST)
        if not to_user.groups.filter(name="cashier").exists():
            return Response(
                {"detail": "Можно переводить только пользователям с ролью cashier."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if to_user.is_superuser or to_user.groups.filter(name="main_cashier").exists():
            return Response(
                {"detail": "Нельзя переводить суперпользователям или main_cashier через этот endpoint."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        to_wallet, _ = Wallet.objects.get_or_create(user=to_user)

        with db_transaction.atomic():
            from_wallet = Wallet.objects.select_for_update().get(pk=from_wallet.pk)
            to_wallet = Wallet.objects.select_for_update().get(pk=to_wallet.pk)
            
            if transaction_type == "deposit":
                # Deposit: main_cashier sends money to cashier
                if from_wallet.balance < amount:
                    return Response(
                        {"detail": f"Недостаточно средств: баланс {from_wallet.balance}, нужно {amount}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                Wallet.objects.filter(pk=from_wallet.pk).update(balance=F("balance") - amount)
                Wallet.objects.filter(pk=to_wallet.pk).update(balance=F("balance") + amount)
            else:  # withdraw
                # Withdraw: main_cashier takes money from cashier
                if to_wallet.balance < amount:
                    return Response(
                        {"detail": f"Недостаточно средств у кассира: баланс {to_wallet.balance}, нужно {amount}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                Wallet.objects.filter(pk=from_wallet.pk).update(balance=F("balance") + amount)
                Wallet.objects.filter(pk=to_wallet.pk).update(balance=F("balance") - amount)
            
            wt = WalletTransfer.objects.create(from_wallet=from_wallet, to_wallet=to_wallet, amount=amount, transaction_type=transaction_type)

        return Response(WalletTransferSerializer(wt).data, status=status.HTTP_201_CREATED)


class SPMTransactionViewSet(viewsets.GenericViewSet):
    """
    ViewSet for SPM (Sports Manager) deposit/withdraw transactions.
    
    Endpoints:
    - POST /api/spm/deposit/ - Deposit to SPM user
    - POST /api/spm/withdraw/ - Withdraw from SPM user
    """
    permission_classes = [AllowAny]
    serializer_class = SPMTransactionSerializer

    def get_permissions(self):
        if getattr(self, "action", None) in {"deposit", "withdraw_send_code", "withdraw"}:
            return [IsSuperAdminOrMainCashierOrCashier()]
        return [AllowAny()]

    def get_serializer_class(self):
        if getattr(self, "action", None) == "get_deposit_status":
            return SPMDepositStatusSerializer
        if getattr(self, "action", None) == "get_user_by_username":
            return SPMGetUserByUserNameSerializer
        if getattr(self, "action", None) == "withdraw_send_code":
            return SPMWithdrawSendCodeSerializer
        if getattr(self, "action", None) == "manage_session":
            return SPMSessionSerializer
        if getattr(self, "action", None) == "register_user":
            return SPMRegisterUserSerializer
        if getattr(self, "action", None) == "withdraw":
            return SPMWithdrawSerializer
        if getattr(self, "action", None) == "deposit":
            return SPMTransactionSerializer
        return super().get_serializer_class()
    
    @swagger_auto_schema(method="post", request_body=SPMTransactionSerializer)
    @action(detail=False, methods=["post"], url_path="deposit")
    def deposit(self, request):
        """
        Deposit funds to SPM user account.
        
        Request body:
        {
            "amount": 100.00,
            "country_code": "TM",
            "phone": "+99365123456",
            "remarks": "Optional deposit note"
        }
        
        Response:
        {
            "balance": 1000.00,
            "txn_id": "unique-transaction-id",
            "message": "Deposit successful"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data["amount"]
        user_name = serializer.validated_data.get("user_name")
        user_id = serializer.validated_data.get("user_id")
        remarks = serializer.validated_data.get("remarks", "")
        txn_id = serializer.validated_data.get("txn_id") or str(uuid.uuid4())

        if not user_name and user_id is not None:
            try:
                spm_client = get_spm_client()
                user_data = spm_client.get_user_by_userid(user_id=user_id)
                if isinstance(user_data, dict):
                    user_name = user_data.get("userName") or user_data.get("user_name")
                user_name = (str(user_name).strip() if user_name else "")
            except SPMApiError as e:
                return Response(
                    {
                        "error": {"message": str(e), "errorCode": e.error_code},
                        "data": None,
                        "statusCode": e.status_code,
                    },
                    status=e.status_code,
                )

        if not user_name:
            return Response(
                {
                    "error": {"message": "userName is required.", "errorCode": "USERNAME_REQUIRED"},
                    "data": None,
                    "statusCode": 400,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet, _ = Wallet.objects.get_or_create(user=request.user)
        with db_transaction.atomic():
            wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
            if wallet.balance < amount:
                return Response(
                    {
                        "error": {
                            "message": f"Недостаточно средств: баланс {wallet.balance}, нужно {amount}.",
                            "errorCode": "INSUFFICIENT_FUNDS",
                        },
                        "data": None,
                        "statusCode": 400,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Wallet.objects.filter(pk=wallet.pk).update(balance=F("balance") - amount)
        
        try:
            # Call SPM API
            spm_client = get_spm_client()
            balance = spm_client.deposit(
                amount=amount,
                user_name=user_name,
                txn_id=txn_id,
                remarks=remarks
            )
            
            return Response(
                {
                    "error": None,
                    "data": SPMTransactionResponseSerializer({"balance": balance, "txn_id": txn_id}).data,
                    "statusCode": 200,
                },
                status=status.HTTP_200_OK,
            )
            
        except SPMApiError as e:
            with db_transaction.atomic():
                Wallet.objects.filter(pk=wallet.pk).update(balance=F("balance") + amount)
            return Response(
                {
                    "error": {
                        "message": str(e),
                        "errorCode": e.error_code
                    },
                    "data": None,
                    "statusCode": e.status_code,
                },
                status=e.status_code
            )
        except Exception as e:
            with db_transaction.atomic():
                Wallet.objects.filter(pk=wallet.pk).update(balance=F("balance") + amount)
            return Response(
                {
                    "error": {
                        "message": f"Internal error: {str(e)}",
                        "errorCode": "INTERNAL_ERROR"
                    },
                    "data": None,
                    "statusCode": 500,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @swagger_auto_schema(method="post", request_body=SPMWithdrawSendCodeSerializer)
    @action(detail=False, methods=["post"], url_path="withdraw/send-code")
    def withdraw_send_code(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_name = serializer.validated_data.get("user_name")
        user_name = (str(user_name).strip() if user_name else "")
        ttl = 60 * 5

        try:
            spm_client = get_spm_client()
            if not user_name:
                return Response(
                    {
                        "error": {"message": "userName is required.", "errorCode": "USERNAME_REQUIRED"},
                        "data": None,
                        "statusCode": 400,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user_data = spm_client.get_user_by_username(user_name=user_name)

            email = None
            if isinstance(user_data, dict):
                for k, v in user_data.items():
                    if isinstance(k, str) and k.lower() == "email":
                        email = v
                        break
            email = (str(email).strip() if email else "")
            if not email:
                return Response(
                    {
                        "error": {
                            "message": "Email not found for this user.",
                            "errorCode": "EMAIL_NOT_FOUND",
                        },
                        "data": None,
                        "statusCode": 400,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            spm_user_id = None
            if isinstance(user_data, dict):
                spm_user_id = user_data.get("userId") or user_data.get("user_id")
            try:
                spm_user_id = int(spm_user_id) if spm_user_id is not None else None
            except Exception:
                spm_user_id = None

            code = f"{secrets.randbelow(1000000):06d}"
            expires_at = timezone.now() + timedelta(seconds=ttl)
            conf = SPMWithdrawConfirmation(user_id=spm_user_id, user_name=user_name, email=email, expires_at=expires_at)
            conf.set_code(code)
            conf.save()

            from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "") or getattr(settings, "EMAIL_HOST_USER", "")
            if not from_email:
                from_email = "no-reply@mobcash.local"

            try:
                send_mail(
                    subject="Withdrawal confirmation code",
                    message=f"Your withdrawal confirmation code is: {code}",
                    from_email=from_email,
                    recipient_list=[email],
                    fail_silently=False,
                )
            except Exception as e:
                conf.delete()
                return Response(
                    {
                        "error": {
                            "message": f"Failed to send email: {str(e)}",
                            "errorCode": "EMAIL_SEND_FAILED",
                        },
                        "data": None,
                        "statusCode": 502,
                    },
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            resp_data = {"sent": True, "expiresIn": ttl, "email": email, "txnId": str(conf.txn_id)}
            if getattr(settings, "DEBUG", False) or getattr(settings, "SPM_WITHDRAW_RETURN_CODE", False):
                resp_data["confirmationCode"] = code
            return Response(
                {
                    "error": None,
                    "data": resp_data,
                    "statusCode": 200,
                },
                status=status.HTTP_200_OK,
            )

        except SPMApiError as e:
            return Response(
                {
                    "error": {"message": str(e), "errorCode": e.error_code},
                    "data": None,
                    "statusCode": e.status_code,
                },
                status=e.status_code,
            )
        except Exception as e:
            return Response(
                {
                    "error": {
                        "message": f"Internal error: {str(e)}",
                        "errorCode": "INTERNAL_ERROR",
                    },
                    "data": None,
                    "statusCode": 500,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
    
    @swagger_auto_schema(method="post", request_body=SPMWithdrawSerializer)
    @action(detail=False, methods=["post"], url_path="withdraw")
    def withdraw(self, request):
        """
        Withdraw funds from SPM user account.
        
        Request body:
        {
            "amount": 50.00,
            "country_code": "TM",
            "phone": "+99365123456",
            "remarks": "Optional withdrawal note"
        }
        
        Response:
        {
            "balance": 950.00,
            "txn_id": "unique-transaction-id",
            "message": "Withdrawal successful"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data["amount"]
        user_name = serializer.validated_data.get("user_name")
        user_id = serializer.validated_data.get("user_id")
        remarks = serializer.validated_data.get("remarks", "")
        txn_id = serializer.validated_data.get("txn_id")
        confirmation_code = serializer.validated_data.get("confirmation_code")

        user_name = (str(user_name).strip() if user_name else "")

        try:
            txn_uuid = uuid.UUID(str(txn_id))
        except Exception:
            return Response(
                {
                    "error": {
                        "message": "Invalid txnId format.",
                        "errorCode": "TXN_ID_INVALID",
                    },
                    "data": None,
                    "statusCode": 400,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not user_name and user_id is not None:
            try:
                spm_client = get_spm_client()
                user_data = spm_client.get_user_by_userid(user_id=user_id)
                if isinstance(user_data, dict):
                    user_name = user_data.get("userName") or user_data.get("user_name")
                user_name = (str(user_name).strip() if user_name else "")
            except SPMApiError as e:
                return Response(
                    {
                        "error": {"message": str(e), "errorCode": e.error_code},
                        "data": None,
                        "statusCode": e.status_code,
                    },
                    status=e.status_code,
                )

        if not user_name:
            return Response(
                {
                    "error": {"message": "userName is required.", "errorCode": "USERNAME_REQUIRED"},
                    "data": None,
                    "statusCode": 400,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        with db_transaction.atomic():
            conf = (
                SPMWithdrawConfirmation.objects.select_for_update()
                .filter(txn_id=txn_uuid, user_name=user_name)
                .first()
            )
            if not conf or conf.is_used or conf.is_expired():
                return Response(
                    {
                        "error": {
                            "message": "Confirmation code expired or not requested.",
                            "errorCode": "CONFIRMATION_CODE_EXPIRED",
                        },
                        "data": None,
                        "statusCode": 400,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if conf.attempts >= conf.max_attempts:
                conf.mark_used()
                conf.save(update_fields=["is_used", "used_at"])
                return Response(
                    {
                        "error": {
                            "message": "Too many attempts.",
                            "errorCode": "CONFIRMATION_CODE_TOO_MANY_ATTEMPTS",
                        },
                        "data": None,
                        "statusCode": 400,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not conf.check_code(str(confirmation_code or "")):
                conf.attempts = conf.attempts + 1
                if conf.attempts >= conf.max_attempts:
                    conf.mark_used()
                    conf.save(update_fields=["attempts", "is_used", "used_at"])
                else:
                    conf.save(update_fields=["attempts"])
                return Response(
                    {
                        "error": {
                            "message": "Invalid confirmation code.",
                            "errorCode": "CONFIRMATION_CODE_INVALID",
                        },
                        "data": None,
                        "statusCode": 400,
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        
        try:
            # Call SPM API
            spm_client = get_spm_client()
            balance = spm_client.withdraw(
                amount=amount,
                user_name=user_name,
                txn_id=str(txn_uuid),
                remarks=remarks
            )

            wallet, _ = Wallet.objects.get_or_create(user=request.user)
            with db_transaction.atomic():
                wallet = Wallet.objects.select_for_update().get(pk=wallet.pk)
                Wallet.objects.filter(pk=wallet.pk).update(balance=F("balance") + amount)
                SPMWithdrawConfirmation.objects.filter(pk=conf.pk).update(is_used=True, used_at=timezone.now())
            
            return Response(
                {
                    "error": None,
                    "data": SPMTransactionResponseSerializer({"balance": balance, "txn_id": str(txn_uuid)}).data,
                    "statusCode": 200,
                },
                status=status.HTTP_200_OK,
            )
            
        except SPMApiError as e:
            return Response(
                {
                    "error": {
                        "message": str(e),
                        "errorCode": e.error_code
                    },
                    "data": None,
                    "statusCode": e.status_code,
                },
                status=e.status_code
            )
        except Exception as e:
            return Response(
                {
                    "error": {
                        "message": f"Internal error: {str(e)}",
                        "errorCode": "INTERNAL_ERROR"
                    },
                    "data": None,
                    "statusCode": 500,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(method="post", request_body=SPMDepositStatusSerializer)
    @action(detail=False, methods=["post"], url_path="deposit/get-status")
    def get_deposit_status(self, request):
        """
        Get the status of a deposit transaction.
        
        Request body:
        {
            "txn_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        
        Response:
        {
            "balance": 1000.00,
            "txn_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        txn_id = serializer.validated_data["txn_id"]
        
        try:
            # Call SPM API
            spm_client = get_spm_client()
            balance = spm_client.get_deposit_status(txn_id=txn_id)
            
            return Response(
                {
                    "error": None,
                    "data": SPMDepositStatusResponseSerializer({"balance": balance}).data,
                    "statusCode": 200,
                },
                status=status.HTTP_200_OK,
            )
            
        except SPMApiError as e:
            return Response(
                {
                    "error": {
                        "message": str(e),
                        "errorCode": e.error_code
                    },
                    "data": None,
                    "statusCode": e.status_code,
                },
                status=e.status_code
            )
        except Exception as e:
            return Response(
                {
                    "error": {
                        "message": f"Internal error: {str(e)}",
                        "errorCode": "INTERNAL_ERROR"
                    },
                    "data": None,
                    "statusCode": 500,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(method="post", request_body=SPMGetUserByUserNameSerializer)
    @action(detail=False, methods=["post"], url_path="get-by-username")
    def get_user_by_username(self, request):
        """
        Get user details by user ID.
        
        Request body:
        {
            "user_id": "user123"
        }
        
        Response:
        {
            "balance": 1000.00,
            "user_name": "John1234569",
            "is_active": true
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_name = serializer.validated_data["user_name"]
        
        try:
            # Call SPM API
            spm_client = get_spm_client()
            user_data = spm_client.get_user_by_username(user_name=user_name)
            
            return Response(
                {
                    "error": None,
                    "data": user_data,
                    "statusCode": 200,
                },
                status=status.HTTP_200_OK,
            )
            
        except SPMApiError as e:
            return Response(
                {
                    "error": {
                        "message": str(e),
                        "errorCode": e.error_code
                    },
                    "data": None,
                    "statusCode": e.status_code,
                },
                status=e.status_code
            )
        except Exception as e:
            return Response(
                {
                    "error": {
                        "message": f"Internal error: {str(e)}",
                        "errorCode": "INTERNAL_ERROR"
                    },
                    "data": None,
                    "statusCode": 500,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(method="post", request_body=SPMSessionSerializer)
    @action(detail=False, methods=["post"], url_path="session")
    def manage_session(self, request):
        """
        Create or destroy a user session.
        
        Request body:
        {
            "user_id": "user123",
            "action": "create"  // or "destroy"
        }
        
        Response:
        {
            "session": "session_token_here",  // null if destroyed
            "message": "Session created successfully"
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = serializer.validated_data["user_id"]
        action = serializer.validated_data["action"]
        
        try:
            # Call SPM API
            spm_client = get_spm_client()
            session_token = spm_client.manage_session(
                user_id=user_id,
                action=action
            )
            
            return Response(
                {
                    "error": None,
                    "data": SPMSessionResponseSerializer({"session": session_token}).data,
                    "statusCode": 200,
                },
                status=status.HTTP_200_OK,
            )
            
        except SPMApiError as e:
            return Response(
                {
                    "error": {
                        "message": str(e),
                        "errorCode": e.error_code
                    },
                    "data": None,
                    "statusCode": e.status_code,
                },
                status=e.status_code
            )
        except Exception as e:
            return Response(
                {
                    "error": {
                        "message": f"Internal error: {str(e)}",
                        "errorCode": "INTERNAL_ERROR"
                    },
                    "data": None,
                    "statusCode": 500,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @swagger_auto_schema(method="post", request_body=SPMRegisterUserSerializer)
    @action(detail=False, methods=["post"], url_path="register")
    def register_user(self, request):
        """
        Register a new user in SPM system.
        
        Request body:
        {
            "names": "John",
            "user_name": "John1234569",
            "email": "john@at.com",
            "country_code": "91",
            "phone": 99900000,
            "password": "PlayerPassword@123"
        }
        
        Response:
        {
            "error": null,
            "data": {
                "user_id": 1,
                "user_name": "John1234569",
                "name": "John"
            },
            "statusCode": 200
        }
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        names = serializer.validated_data["names"]
        user_name = serializer.validated_data["user_name"]
        email = serializer.validated_data["email"]
        country_code = serializer.validated_data["country_code"]
        phone = serializer.validated_data["phone"]
        password = serializer.validated_data["password"]
        
        try:
            # Call SPM API
            spm_client = get_spm_client()
            user_data = spm_client.register_user(
                names=names,
                user_name=user_name,
                email=email,
                country_code=country_code,
                phone=phone,
                password=password
            )
            
            # Return success response in SPM format
            return Response(
                {
                    "error": None,
                    "data": SPMRegisterUserResponseSerializer(user_data).data,
                    "statusCode": 200
                },
                status=status.HTTP_200_OK
            )
            
        except SPMApiError as e:
            return Response(
                {
                    "error": {
                        "message": str(e),
                        "errorCode": e.error_code
                    },
                    "data": None,
                    "statusCode": e.status_code
                },
                status=e.status_code
            )
        except Exception as e:
            return Response(
                {
                    "error": {
                        "message": f"Internal error: {str(e)}",
                        "errorCode": "INTERNAL_ERROR"
                    },
                    "data": None,
                    "statusCode": 500
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


