from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .cashier_views import CashierAccountViewSet

router = DefaultRouter()
router.register(r"users", CashierAccountViewSet, basename="cashier-users")

urlpatterns = [
    path("", include(router.urls)),
]


