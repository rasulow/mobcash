from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction as db_transaction
from django.db.models import F
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.external_api import ExternalApiError, fetch_yildiztop_users_by_referral_token, post_yildiztop_update_balance
from core.models import Transaction, Wallet, WalletTransfer
from core.spm_api import get_spm_client, SPMApiError

from .permissions import IsMainCashier
from .serializers import (
    SPMTransactionResponseSerializer,
    SPMTransactionSerializer,
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

    def create(self, request, *args, **kwargs):
        ser = WalletTransferCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        to_user_id = ser.validated_data["to_user_id"]
        amount: Decimal = ser.validated_data["amount"]

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
            if from_wallet.balance < amount:
                return Response(
                    {"detail": f"Недостаточно средств: баланс {from_wallet.balance}, нужно {amount}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            Wallet.objects.filter(pk=from_wallet.pk).update(balance=F("balance") - amount)
            Wallet.objects.filter(pk=to_wallet.pk).update(balance=F("balance") + amount)
            wt = WalletTransfer.objects.create(from_wallet=from_wallet, to_wallet=to_wallet, amount=amount)

        return Response(WalletTransferSerializer(wt).data, status=status.HTTP_201_CREATED)


class SPMTransactionViewSet(viewsets.GenericViewSet):
    """
    ViewSet for SPM (Sports Manager) deposit/withdraw transactions.
    
    Endpoints:
    - POST /api/spm/deposit/ - Deposit to SPM user
    - POST /api/spm/withdraw/ - Withdraw from SPM user
    """
    serializer_class = SPMTransactionSerializer
    
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
        serializer = SPMTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data["amount"]
        country_code = serializer.validated_data["country_code"]
        phone = serializer.validated_data["phone"]
        remarks = serializer.validated_data.get("remarks", "")
        
        # Generate unique transaction ID
        import uuid
        txn_id = str(uuid.uuid4())
        
        try:
            # Call SPM API
            spm_client = get_spm_client()
            balance = spm_client.deposit(
                amount=amount,
                country_code=country_code,
                phone=phone,
                txn_id=txn_id,
                remarks=remarks
            )
            
            # Return success response
            response_data = {
                "balance": balance,
                "txn_id": txn_id,
                "message": "Deposit successful"
            }
            return Response(
                SPMTransactionResponseSerializer(response_data).data,
                status=status.HTTP_200_OK
            )
            
        except SPMApiError as e:
            return Response(
                {
                    "error": {
                        "message": str(e),
                        "errorCode": e.error_code
                    }
                },
                status=e.status_code
            )
        except Exception as e:
            return Response(
                {
                    "error": {
                        "message": f"Internal error: {str(e)}",
                        "errorCode": "INTERNAL_ERROR"
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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
        serializer = SPMTransactionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        amount = serializer.validated_data["amount"]
        country_code = serializer.validated_data["country_code"]
        phone = serializer.validated_data["phone"]
        remarks = serializer.validated_data.get("remarks", "")
        
        # Generate unique transaction ID
        import uuid
        txn_id = str(uuid.uuid4())
        
        try:
            # Call SPM API
            spm_client = get_spm_client()
            balance = spm_client.withdraw(
                amount=amount,
                country_code=country_code,
                phone=phone,
                txn_id=txn_id,
                remarks=remarks
            )
            
            # Return success response
            response_data = {
                "balance": balance,
                "txn_id": txn_id,
                "message": "Withdrawal successful"
            }
            return Response(
                SPMTransactionResponseSerializer(response_data).data,
                status=status.HTTP_200_OK
            )
            
        except SPMApiError as e:
            return Response(
                {
                    "error": {
                        "message": str(e),
                        "errorCode": e.error_code
                    }
                },
                status=e.status_code
            )
        except Exception as e:
            return Response(
                {
                    "error": {
                        "message": f"Internal error: {str(e)}",
                        "errorCode": "INTERNAL_ERROR"
                    }
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


