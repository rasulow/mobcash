from django.contrib.auth import get_user_model
from rest_framework import mixins, viewsets

from .cashier_serializers import CashierAccountCreateSerializer
from .permissions import IsSuperAdminOrMainCashier

User = get_user_model()


class CashierAccountViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    """
    Create cashier accounts.
    - superadmin: allowed
    - main_cashier: allowed
    Group is forced to "cashier".
    """

    queryset = User.objects.all()
    serializer_class = CashierAccountCreateSerializer
    permission_classes = [IsSuperAdminOrMainCashier]


