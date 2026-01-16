from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class MobcashTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Extends token response with user role info:
    - superadmin
    - main_cashier
    - cashier
    - user (default)
    """

    @classmethod
    def get_token(cls, user):
        return super().get_token(user)

    def validate(self, attrs):
        data = super().validate(attrs)
        user = self.user

        groups = list(user.groups.values_list("name", flat=True))
        if user.is_superuser:
            role = "superadmin"
        elif "main_cashier" in groups:
            role = "main_cashier"
        elif "cashier" in groups:
            role = "cashier"
        else:
            role = "user"

        data["user"] = {
            "id": user.id,
            "username": user.get_username(),
            "is_superuser": bool(user.is_superuser),
            "is_staff": bool(user.is_staff),
            "groups": groups,
            "role": role,
        }
        return data


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    def validate_old_password(self, value):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.check_password(value):
            raise serializers.ValidationError("Неверный текущий пароль.")
        return value

    def validate(self, attrs):
        new_password = attrs.get("new_password")
        new_password2 = attrs.get("new_password2")

        if new_password != new_password2:
            raise serializers.ValidationError({"new_password2": "Пароли не совпадают."})

        request = self.context.get("request")
        user = getattr(request, "user", None)
        try:
            password_validation.validate_password(new_password, user=user)
        except DjangoValidationError as e:
            raise serializers.ValidationError({"new_password": list(e.messages)})

        return attrs


