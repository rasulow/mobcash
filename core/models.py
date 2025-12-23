from decimal import Decimal

from django.conf import settings
from django.db import models
from django.db.models import Case, DecimalField, F, Sum, Value, When


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
    )
    currency = models.CharField(max_length=8, default="USD")

    def __str__(self) -> str:
        return f"{self.user} ({self.currency})"

    @property
    def balance(self) -> Decimal:
        signed_amount_expr = Case(
            When(type=Transaction.Type.WITHDRAW, then=F("amount") * Value(-1)),
            default=F("amount"),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        )
        total = (
            self.transactions.filter(status=Transaction.Status.APPROVED).aggregate(
                s=Sum(signed_amount_expr)
            )["s"]
            or Decimal("0")
        )
        return Decimal(total)


class Transaction(models.Model):
    class Type(models.TextChoices):
        DEPOSIT = "deposit", "Deposit"
        WITHDRAW = "withdraw", "Withdraw"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    type = models.CharField(max_length=16, choices=Type.choices)
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    note = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.wallet.user} {self.type} {self.amount} ({self.status})"

    @property
    def signed_amount(self) -> Decimal:
        if self.type == self.Type.WITHDRAW:
            return -self.amount
        return self.amount

# Create your models here.
