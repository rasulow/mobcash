from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView

from .auth_serializers import ChangePasswordSerializer, MobcashTokenObtainPairSerializer


class MobcashTokenObtainPairView(TokenObtainPairView):
    serializer_class = MobcashTokenObtainPairSerializer


class ChangePasswordView(generics.GenericAPIView):
    serializer_class = ChangePasswordSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        ser = self.get_serializer(data=request.data, context={"request": request})
        ser.is_valid(raise_exception=True)
        request.user.set_password(ser.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"detail": "Пароль успешно изменён."}, status=status.HTTP_200_OK)


