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


