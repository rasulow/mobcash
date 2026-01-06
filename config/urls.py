"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="MobCash API",
        default_version="v1",
        description="MobCash API (DRF)",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
    authentication_classes=(),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("", include("core.urls")),
    path("api/", include("core.api.urls")),
    path("api/auth/", include("core.api.auth_urls")),
    path("api/cashier/", include("core.api.cashier_urls")),
    path("api/admin/", include("core.api.admin_urls")),
    path(
        "api/docs/",
        schema_view.with_ui("swagger", cache_timeout=0),
        name="schema-swagger-ui",
    ),
    path("api/redoc/", schema_view.with_ui("redoc", cache_timeout=0), name="schema-redoc"),
    path("accounts/logout/", auth_views.LogoutView.as_view(next_page="login"), name="logout"),
    path("accounts/", include("django.contrib.auth.urls")),
]
