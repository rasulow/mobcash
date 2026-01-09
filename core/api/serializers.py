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
        fields = ["id", "from_user_id", "from_username", "to_user_id", "to_username", "amount", "transaction_type", "created_at"]


class WalletTransferCreateSerializer(serializers.Serializer):
    to_user_id = serializers.IntegerField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    transaction_type = serializers.ChoiceField(choices=['deposit', 'withdraw'], help_text="Transaction type: deposit or withdraw")


class SPMTransactionSerializer(serializers.Serializer):
    """Serializer for SPM deposit/withdraw requests"""
    amount = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        help_text="Amount in SPM currency"
    )
    country_code = serializers.CharField(
        max_length=2,
        help_text="Country code (e.g., TM, UZ)"
    )
    phone = serializers.CharField(
        max_length=20,
        help_text="User's phone number"
    )
    remarks = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Optional transaction remarks"
    )


class SPMTransactionResponseSerializer(serializers.Serializer):
    """Serializer for SPM transaction response"""
    balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Updated balance after transaction"
    )
    txn_id = serializers.CharField(
        help_text="Transaction ID"
    )
    message = serializers.CharField(
        help_text="Success message"
    )


class SPMDepositStatusSerializer(serializers.Serializer):
    """Serializer for checking deposit status"""
    txn_id = serializers.CharField(
        max_length=255,
        help_text="Transaction ID to check"
    )


class SPMDepositStatusResponseSerializer(serializers.Serializer):
    """Serializer for deposit status response"""
    balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Current balance"
    )
    txn_id = serializers.CharField(
        help_text="Transaction ID"
    )


class SPMGetUserByPhoneSerializer(serializers.Serializer):
    """Serializer for getting user by phone"""
    country_code = serializers.CharField(
        max_length=2,
        help_text="Country code (e.g., TM, UZ)"
    )
    phone = serializers.CharField(
        max_length=20,
        help_text="User's phone number"
    )


class SPMUserResponseSerializer(serializers.Serializer):
    """Serializer for user details response"""
    balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="User's balance"
    )
    user_name = serializers.CharField(
        help_text="User's username"
    )
    is_active = serializers.BooleanField(
        help_text="Whether user is active"
    )


class SPMSessionSerializer(serializers.Serializer):
    """Serializer for session management"""
    user_id = serializers.CharField(
        max_length=255,
        help_text="User ID in SPM system"
    )
    action = serializers.ChoiceField(
        choices=["create", "destroy"],
        help_text="Action to perform: 'create' or 'destroy'"
    )


class SPMSessionResponseSerializer(serializers.Serializer):
    """Serializer for session response"""
    session = serializers.CharField(
        allow_null=True,
        help_text="Session token (null if destroyed)"
    )
    message = serializers.CharField(
        help_text="Success message"
    )


class SPMRegisterUserSerializer(serializers.Serializer):
    """Serializer for user registration request"""
    names = serializers.CharField(
        max_length=255,
        help_text="User's full name"
    )
    user_name = serializers.CharField(
        max_length=255,
        help_text="Unique username"
    )
    email = serializers.EmailField(
        help_text="User's email address"
    )
    country_code = serializers.CharField(
        max_length=10,
        help_text="Country code (e.g., '91', 'TM')"
    )
    phone = serializers.IntegerField(
        help_text="Phone number as integer"
    )
    password = serializers.CharField(
        max_length=255,
        help_text="User password (min 8 chars, must have capital & small letter, number, symbol)"
    )


class SPMRegisterUserResponseSerializer(serializers.Serializer):
    """Serializer for user registration response"""
    user_id = serializers.IntegerField(
        help_text="Registered user ID"
    )
    user_name = serializers.CharField(
        help_text="Username"
    )
    name = serializers.CharField(
        help_text="User's full name"
    )


