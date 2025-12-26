from django.conf import settings
from django.db import models
from django.db.models import DecimalField


class Wallet(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="wallet",
        verbose_name="Пользователь",
    )
    currency = models.CharField(max_length=8, default="TMT", verbose_name="Валюта")
    balance = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, verbose_name="Баланс"
    )

    class Meta:
        verbose_name = "Кошелёк"
        verbose_name_plural = "Кошельки"

    def __str__(self) -> str:
        return f"{self.user} ({self.currency})"


class Transaction(models.Model):
    class ExternalSyncStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        SYNCED = "synced", "Synced"
        FAILED = "failed", "Failed"

    class Type(models.TextChoices):
        DEPOSIT = "deposit", "Депозит"
        WITHDRAW = "withdraw", "Вывод"

    wallet = models.ForeignKey(
        Wallet,
        on_delete=models.CASCADE,
        related_name="transactions",
        verbose_name="Кошелёк",
    )
    external_user_id = models.PositiveIntegerField(
        null=True, blank=True, db_index=True, verbose_name="ID клиента"
    )
    external_user_name = models.CharField(
        max_length=255, blank=True, default="", verbose_name="Клиент"
    )
    external_user_email = models.EmailField(blank=True, default="", verbose_name="Email клиента")
    external_referral_token = models.CharField(
        max_length=64, blank=True, default="", db_index=True, verbose_name="Токен"
    )
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
        verbose_name="Статус синхронизации",
    )
    external_sync_error = models.TextField(blank=True, default="", verbose_name="Ошибка синхронизации")
    type = models.CharField(
        max_length=16,
        choices=Type.choices,
        default=Type.WITHDRAW,
        verbose_name="Тип",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Сумма")
    note = models.CharField(max_length=255, blank=True, default="", verbose_name="Комментарий")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата изменения")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"

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
        verbose_name="Откуда",
    )
    to_wallet = models.ForeignKey(
        Wallet,
        on_delete=models.PROTECT,
        related_name="incoming_transfers",
        verbose_name="Кому",
    )
    amount = models.DecimalField(max_digits=12, decimal_places=2, verbose_name="Сумма")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата")

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Перевод кошелька"
        verbose_name_plural = "Переводы кошельков"

    def __str__(self) -> str:
        return f"{self.from_wallet.user} -> {self.to_wallet.user}: {self.amount}"

