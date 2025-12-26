from django.conf import settings
from django.db import models
from django.db.models import DecimalField


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
    )
    currency = models.CharField(max_length=8, default="TMT")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self) -> str:
        return f"{self.user} ({self.currency})"


class Transaction(models.Model):
    class ExternalSyncStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SYNCED = "synced", "Synced"
        FAILED = "failed", "Failed"

    class Type(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        WITHDRAW = "withdraw", "Withdraw"

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    external_user_id = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    external_user_name = models.CharField(max_length=255, blank=True, default="")
    external_user_email = models.EmailField(blank=True, default="")
    external_referral_token = models.CharField(max_length=64, blank=True, default="", db_index=True)
    external_balance_before = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    external_balance_after = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    external_sync_status = models.CharField(
        max_length=16,
        choices=ExternalSyncStatus.choices,
        default=ExternalSyncStatus.PENDING,
    )
    external_sync_error = models.TextField(blank=True, default="")
    type = models.CharField(
        max_length=16,
        choices=Type.choices,
        default=Type.WITHDRAW,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        who = self.external_user_name or self.wallet.user
        return f"{who} {self.type} {self.amount} @ {self.created_at:%Y-%m-%d %H:%M}"

class WalletTransfer(models.Model):
    """
    Internal transfer between local wallets (no external API).
    Used by main_cashier to deposit to other users using their own wallet balance.
    """

    from_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name="outgoing_transfers",
    )
    to_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.from_wallet.user} -> {self.to_wallet.user}: {self.amount}"

