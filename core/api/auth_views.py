from rest_framework_simplejwt.views import TokenObtainPairView

from .auth_serializers import MobcashTokenObtainPairSerializer


class MobcashTokenObtainPairView(TokenObtainPairView):
    serializer_class = MobcashTokenObtainPairSerializer


