from django.contrib import admin

from .models import Transaction, Wallet


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("user", "currency")
    search_fields = ("user__username", "user__email")


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ("wallet", "type", "amount", "status", "created_at")
    list_filter = ("type", "status", "created_at")
    search_fields = ("wallet__user__username", "wallet__user__email", "note")

# Register your models here.
