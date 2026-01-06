from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers

from core.models import Transaction, Wallet, WalletTransfer

User = get_user_model()


class WalletSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Wallet
        fields = ["id", "user_id", "username", "currency", "balance"]


class TransactionSerializer(serializers.ModelSerializer):
    wallet_user_id = serializers.IntegerField(source="wallet.user_id", read_only=True)
    wallet_username = serializers.CharField(source="wallet.user.username", read_only=True)
    type_label = serializers.CharField(source="get_type_display", read_only=True)

    class Meta:
        model = Transaction
        fields = [
            "id",
            "wallet_user_id",
            "wallet_username",
            "type",
            "type_label",
            "external_referral_token",
            "external_user_name",
            "external_user_email",
            "amount",
            "note",
            "external_sync_status",
            "external_sync_error",
            "created_at",
        ]
        read_only_fields = [
            "external_sync_status",
            "external_sync_error",
            "created_at",
        ]


class TransactionCreateSerializer(serializers.Serializer):
    referral_token = serializers.CharField(max_length=64)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    type = serializers.ChoiceField(choices=Transaction.Type.choices)
    note = serializers.CharField(max_length=255, required=False, allow_blank=True)


class WalletTransferSerializer(serializers.ModelSerializer):
    from_user_id = serializers.IntegerField(source="from_wallet.user_id", read_only=True)
    from_username = serializers.CharField(source="from_wallet.user.username", read_only=True)
    to_user_id = serializers.IntegerField(source="to_wallet.user_id", read_only=True)
    to_username = serializers.CharField(source="to_wallet.user.username", read_only=True)

    class Meta:
        model = WalletTransfer
        fields = ["id", "from_user_id", "from_username", "to_user_id", "to_username", "amount", "created_at"]


class WalletTransferCreateSerializer(serializers.Serializer):
    to_user_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))


