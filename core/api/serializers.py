from decimal import Decimal
from collections.abc import Mapping

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
    userName = serializers.CharField(
        source="user_name",
        required=False,
        allow_blank=False,
        help_text="Username in SPM system"
    )
    userId = serializers.IntegerField(
        source="user_id",
        required=False,
        help_text="User ID in SPM system (legacy)"
    )
    txnId = serializers.CharField(
        max_length=255,
        source="txn_id",
        required=False,
        allow_blank=True,
        help_text="Transaction ID"
    )
    remarks = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
        help_text="Optional transaction remarks"
    )

    def validate(self, attrs):
        if not attrs.get("user_name") and attrs.get("user_id") is None:
            raise serializers.ValidationError({"userName": ["Обязательное поле."]})
        return attrs

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            data = data.copy()
            if "userName" not in data and "user_name" in data:
                data["userName"] = data["user_name"]
            if "userId" not in data and "user_id" in data:
                data["userId"] = data["user_id"]
            if "txnId" not in data and "txn_id" in data:
                data["txnId"] = data["txn_id"]
        return super().to_internal_value(data)


class SPMWithdrawSerializer(SPMTransactionSerializer):
    txnId = serializers.CharField(
        max_length=255,
        source="txn_id",
        help_text="Transaction ID"
    )
    confirmationCode = serializers.CharField(
        max_length=32,
        source="confirmation_code",
        help_text="Confirmation code sent to the user's email"
    )

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            data = data.copy()
            if "confirmationCode" not in data and "confirmation_code" in data:
                data["confirmationCode"] = data["confirmation_code"]
        return super().to_internal_value(data)


class SPMWithdrawSendCodeSerializer(serializers.Serializer):
    userName = serializers.CharField(
        source="user_name",
        required=True,
        allow_blank=False,
        help_text="Username in SPM system"
    )

    def validate(self, attrs):
        if not attrs.get("user_name"):
            raise serializers.ValidationError({"userName": ["Обязательное поле."]})
        return attrs

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            data = data.copy()
            if "userName" not in data and "user_name" in data:
                data["userName"] = data["user_name"]
        return super().to_internal_value(data)


class SPMTransactionResponseSerializer(serializers.Serializer):
    """Serializer for SPM transaction response"""
    balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Updated balance after transaction"
    )
    txnId = serializers.CharField(
        max_length=255,
        source="txn_id",
        help_text="Transaction ID"
    )
    


class SPMDepositStatusSerializer(serializers.Serializer):
    """Serializer for checking deposit status"""
    txnId = serializers.CharField(
        max_length=255,
        source="txn_id",
        help_text="Transaction ID to check"
    )

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            data = data.copy()
            if "txnId" not in data and "txn_id" in data:
                data["txnId"] = data["txn_id"]
        return super().to_internal_value(data)


class SPMDepositStatusResponseSerializer(serializers.Serializer):
    """Serializer for deposit status response"""
    balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Current balance"
    )
    


class SPMGetUserByPhoneSerializer(serializers.Serializer):
    """Serializer for getting user by phone"""
    countryCode = serializers.CharField(
        max_length=2,
        source="country_code",
        help_text="Country code (e.g., TM, UZ)"
    )
    phone = serializers.CharField(max_length=20, help_text="User's phone number")

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            data = data.copy()
            if "countryCode" not in data and "country_code" in data:
                data["countryCode"] = data["country_code"]
        return super().to_internal_value(data)


class SPMGetUserByUserIdSerializer(serializers.Serializer):
    """Serializer for getting user by userId"""
    userId = serializers.IntegerField(
        source="user_id",
        help_text="User ID in SPM system"
    )

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            data = data.copy()
            if "userId" not in data and "user_id" in data:
                data["userId"] = data["user_id"]
        return super().to_internal_value(data)


class SPMGetUserByUserNameSerializer(serializers.Serializer):
    """Serializer for getting user by userName"""
    userName = serializers.CharField(
        max_length=255,
        source="user_name",
        help_text="Username in SPM system"
    )

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            data = data.copy()
            if "userName" not in data and "user_name" in data:
                data["userName"] = data["user_name"]
        return super().to_internal_value(data)


class SPMUserResponseSerializer(serializers.Serializer):
    """Serializer for user details response"""
    balance = serializers.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="User's balance"
    )
    userName = serializers.CharField(help_text="User's username")
    isActive = serializers.BooleanField(help_text="Whether user is active")


class SPMSessionSerializer(serializers.Serializer):
    """Serializer for session management"""
    userId = serializers.CharField(
        max_length=255,
        source="user_id",
        help_text="User ID in SPM system"
    )
    action = serializers.ChoiceField(
        choices=["create", "destroy"],
        help_text="Action to perform: 'create' or 'destroy'"
    )

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            data = data.copy()
            if "userId" not in data and "user_id" in data:
                data["userId"] = data["user_id"]
        return super().to_internal_value(data)


class SPMSessionResponseSerializer(serializers.Serializer):
    """Serializer for session response"""
    session = serializers.CharField(
        allow_null=True,
        help_text="Session token (null if destroyed)"
    )
    


class SPMRegisterUserSerializer(serializers.Serializer):
    """Serializer for user registration request"""
    names = serializers.CharField(
        max_length=255,
        help_text="User's full name"
    )
    userName = serializers.CharField(
        max_length=255,
        source="user_name",
        help_text="Unique username"
    )
    email = serializers.CharField(max_length=255, help_text="User's email address")
    countryCode = serializers.CharField(
        max_length=10,
        source="country_code",
        help_text="Country code (e.g., '91', 'TM')"
    )
    phone = serializers.IntegerField(
        help_text="Phone number as integer"
    )
    password = serializers.CharField(
        max_length=255,
        help_text="User password (min 8 chars, must have capital & small letter, number, symbol)"
    )

    def to_internal_value(self, data):
        if isinstance(data, Mapping):
            data = data.copy()
            if "userName" not in data and "user_name" in data:
                data["userName"] = data["user_name"]
            if "countryCode" not in data and "country_code" in data:
                data["countryCode"] = data["country_code"]
        return super().to_internal_value(data)


class SPMRegisterUserResponseSerializer(serializers.Serializer):
    """Serializer for user registration response"""
    userId = serializers.IntegerField(help_text="Registered user ID")
    userName = serializers.CharField(help_text="Username")
    name = serializers.CharField(
        help_text="User's full name"
    )


