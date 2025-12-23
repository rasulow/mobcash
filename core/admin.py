from django.contrib import admin
from unfold.admin import ModelAdmin

from .models import Transaction, Wallet


@admin.register(Wallet)
class WalletAdmin(ModelAdmin):
    list_display = ("user", "currency", "balance")
    search_fields = ("user__username", "user__email")


@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = (
        "id",
        "wallet_user",
        "external_referral_token",
        "external_user_name",
        "amount",
        "created_at",
    )
    list_filter = ("created_at",)
    search_fields = (
        "wallet__user__username",
        "wallet__user__email",
        "external_user_name",
        "external_user_email",
        "external_referral_token",
    )

    @admin.display(description="User", ordering="wallet__user__username")
    def wallet_user(self, obj: Transaction) -> str:
        return obj.wallet.user.get_username()

    # Make transactions immutable in admin (read-only history)
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # Allow viewing (with view permission) but disallow edits.
        return False

    def has_delete_permission(self, request, obj=None):
        return False

# Register your models here.
