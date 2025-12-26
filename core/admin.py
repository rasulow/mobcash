from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin

from .models import Transaction, Wallet, WalletTransfer

User = get_user_model()


# Re-register User/Group with Unfold ModelAdmin
try:
    admin.site.unregister(User)
except admin.sites.NotRegistered:
    pass

try:
    admin.site.unregister(Group)
except admin.sites.NotRegistered:
    pass


class UnfoldUserCreationForm(UserCreationForm):
    """
    Ensure admin-created users get a properly hashed password.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    add_form = UnfoldUserCreationForm
    form = UserChangeForm

    list_display = ("id", "username", "email", "is_staff", "is_superuser", "is_active", "last_login")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("id",)

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                    "groups",
                ),
            },
        ),
    )


@admin.register(Group)
class GroupAdmin(ModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)


@admin.register(Wallet)
class WalletAdmin(ModelAdmin):
    list_display = ("user", "currency", "balance")
    search_fields = ("user__username", "user__email")


@admin.register(Transaction)
class TransactionAdmin(ModelAdmin):
    list_display = (
        "id",
        "wallet_user",
        "type",
        "external_referral_token",
        "external_user_name",
        "amount",
        "created_at_fmt",
    )
    list_filter = (
        ("wallet__user", admin.RelatedOnlyFieldListFilter),
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = (
        "wallet__user__username",
        "wallet__user__email",
        "external_user_name",
        "external_user_email",
        "external_referral_token",
    )

    @admin.display(description="Пользователь", ordering="wallet__user__username")
    def wallet_user(self, obj: Transaction) -> str:
        return obj.wallet.user.get_username()

    @admin.display(description="Дата", ordering="created_at")
    def created_at_fmt(self, obj: Transaction) -> str:
        # dd.mm.YYYY hh:mm:ss
        return obj.created_at.strftime("%d.%m.%Y %H:%M:%S")


@admin.register(WalletTransfer)
class WalletTransferAdmin(ModelAdmin):
    list_display = ("id", "from_wallet", "to_wallet", "amount", "created_at")
    list_filter = (
        ("from_wallet__user", admin.RelatedOnlyFieldListFilter),
        ("to_wallet__user", admin.RelatedOnlyFieldListFilter),
        ("created_at", admin.DateFieldListFilter),
    )
    search_fields = (
        "from_wallet__user__username",
        "to_wallet__user__username",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False