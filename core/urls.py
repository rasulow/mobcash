from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("transactions/new/", views.transaction_create, name="transaction_create"),
    path("cashier/deposit/", views.cashier_deposit, name="cashier_deposit"),
    path("api/clients/", views.api_clients, name="api_clients"),
]


