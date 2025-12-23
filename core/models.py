from django.conf import settings
from django.db import models
from django.db.models import DecimalField


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
    )
    currency = models.CharField(max_length=8, default="USD")
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self) -> str:
        return f"{self.user} ({self.currency})"


class Transaction(models.Model):
    class ExternalSyncStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SYNCED = "synced", "Synced"
        FAILED = "failed", "Failed"

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
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        who = self.external_user_name or self.wallet.user
        return f"{who} {self.amount} @ {self.created_at:%Y-%m-%d %H:%M}"

# Create your models here.
