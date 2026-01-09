from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from rest_framework import serializers

from core.models import Transaction, Wallet, WalletTransfer

User = get_user_model()


class AdminUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=False)
    groups = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all(), many=True, required=False)
    wallet = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "wallet",
            "password",
        ]

    def get_wallet(self, obj):
        # Reverse one-to-one relation: may not exist for some users.
        try:
            wallet = obj.wallet
        except Wallet.DoesNotExist:
            return None
        return AdminWalletSerializer(wallet).data

    def create(self, validated_data):
        password = validated_data.pop("password", None)
        groups = validated_data.pop("groups", [])
        user = User(**validated_data)
        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()
        user.save()
        if groups:
            user.groups.set(groups)
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        groups = validated_data.pop("groups", None)
        for k, v in validated_data.items():
            setattr(instance, k, v)
        if password:
            instance.set_password(password)
        instance.save()
        if groups is not None:
            instance.groups.set(groups)
        return instance


class WalletSetBalanceSerializer(serializers.Serializer):
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)


class AdminGroupSerializer(serializers.ModelSerializer):
    permissions = serializers.PrimaryKeyRelatedField(
        queryset=Permission.objects.all(), many=True, required=False
    )

    class Meta:
        model = Group
        fields = ["id", "name", "permissions"]


class WalletCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    currency = serializers.CharField(max_length=8, default="TMT", required=False)
    balance = serializers.DecimalField(max_digits=12, decimal_places=2, default=0, min_value=0, required=False)


class AdminWalletSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(source="user.id", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = Wallet
        fields = ["id", "user_id", "username", "currency", "balance"]


class AdminTransactionSerializer(serializers.ModelSerializer):
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


class AdminWalletTransferSerializer(serializers.ModelSerializer):
    from_user_id = serializers.IntegerField(source="from_wallet.user_id", read_only=True)
    from_username = serializers.CharField(source="from_wallet.user.username", read_only=True)
    to_user_id = serializers.IntegerField(source="to_wallet.user_id", read_only=True)
    to_username = serializers.CharField(source="to_wallet.user.username", read_only=True)

    class Meta:
        model = WalletTransfer
        fields = ["id", "from_user_id", "from_username", "to_user_id", "to_username", "amount", "created_at"]


