from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView

from .auth_views import ChangePasswordView, MobcashTokenObtainPairView

urlpatterns = [
    path("token/", MobcashTokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("password/change/", ChangePasswordView.as_view(), name="password_change"),
]


