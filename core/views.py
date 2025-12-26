from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.http import JsonResponse
from django.db import transaction as db_transaction
from django.db.models import F

from .forms import CashierDepositForm, TransactionCreateForm
from .external_api import (
    ExternalApiError,
    fetch_yildiztop_users_by_referral_token,
    fetch_yildiztop_users,
    post_yildiztop_update_balance,
)
from .models import Transaction, Wallet, WalletTransfer
from .permissions import is_main_cashier, main_cashier_required


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


@login_required
def dashboard(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    cashier = is_main_cashier(request.user)
    if cashier:
        user_id = (request.GET.get("user") or "").strip()
        qs = Transaction.objects.select_related("wallet", "wallet__user").all()
        if user_id:
            qs = qs.filter(wallet__user_id=user_id)
        transactions = qs[:25]
        user_choices = (
            Transaction.objects.select_related("wallet__user")
            .values("wallet__user_id", "wallet__user__username")
            .distinct()
            .order_by("wallet__user__username")
        )
    else:
        transactions = wallet.transactions.all()[:10]
        user_id = ""
        user_choices = []
    return render(
        request,
        "core/dashboard.html",
        {
            "wallet": wallet,
            "transactions": transactions,
            "is_cashier": cashier,
            "filter_user_id": user_id,
            "user_choices": user_choices,
        },
    )


@main_cashier_required
def cashier_deposit(request):
    from_wallet, _ = Wallet.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = CashierDepositForm(request.POST)
        if form.is_valid():
            to_user = form.cleaned_data["to_user"]
            amount = form.cleaned_data["amount"]
            to_wallet, _ = Wallet.objects.get_or_create(user=to_user)

            with db_transaction.atomic():
                from_wallet = Wallet.objects.select_for_update().get(pk=from_wallet.pk)
                to_wallet = Wallet.objects.select_for_update().get(pk=to_wallet.pk)

                if from_wallet.balance < amount:
                    messages.warning(request, f"Недостаточно средств: у вас {from_wallet.balance}, нужно {amount}.")
                    return redirect("cashier_deposit")

                Wallet.objects.filter(pk=from_wallet.pk).update(balance=F("balance") - amount)
                Wallet.objects.filter(pk=to_wallet.pk).update(balance=F("balance") + amount)
                WalletTransfer.objects.create(
                    from_wallet=from_wallet,
                    to_wallet=to_wallet,
                    amount=amount,
                )

            messages.success(request, "Пополнение выполнено.")
            return redirect("dashboard")
    else:
        form = CashierDepositForm()

    return render(request, "core/cashier_deposit.html", {"form": form, "wallet": from_wallet})


@login_required
def transaction_create(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    try:
        external_users = fetch_yildiztop_users()
    except ExternalApiError:
        external_users = []

    user_by_id = {str(u.id): u for u in external_users}
    client_choices = [(str(u.id), u.label) for u in external_users]

    if not client_choices:
        messages.warning(request, "Список клиентов временно недоступен (внешний API). Попробуйте позже.")

    if request.method == "POST":
        form = TransactionCreateForm(request.POST, client_choices=client_choices)
        if form.is_valid():
            client_id = form.cleaned_data["client_id"]
            ext_user = user_by_id.get(str(client_id))
            if not ext_user:
                messages.error(request, "Выбранный клиент некорректен. Попробуйте снова.")
                return redirect("transaction_create")

            # Don't store a transaction if there isn't enough money.
            amount = form.cleaned_data["amount"]
            tx_type = form.cleaned_data["type"]
            if tx_type == Transaction.Type.DEPOSIT and (wallet.balance is None or Decimal(wallet.balance) < amount):
                messages.warning(request, f"Не отправлено: сумма {amount} больше вашего баланса {wallet.balance}.")
                return redirect("dashboard")

            # Try external update-balance right away.
            try:
                tx = form.save(commit=False)
                tx.wallet = wallet
                tx.external_user_id = int(ext_user.id)
                tx.external_user_name = ext_user.name
                tx.external_user_email = ext_user.email or ""
                tx.external_referral_token = ext_user.referral_token or ""
                tx.external_sync_status = Transaction.ExternalSyncStatus.PENDING
                tx.external_sync_error = ""

                token = tx.external_referral_token
                signed_amount = tx.amount if tx.type == Transaction.Type.DEPOSIT else -tx.amount
                post_yildiztop_update_balance(token, signed_amount)

                tx.external_sync_status = Transaction.ExternalSyncStatus.SYNCED
                tx.external_sync_error = ""
                tx.save()

                # Update our wallet balance only after external update succeeded.
                # Requirement: WITHDRAW must NOT decrease own balance.
                if tx.type == Transaction.Type.DEPOSIT:
                    with db_transaction.atomic():
                        updated = Wallet.objects.filter(pk=wallet.pk, balance__gte=tx.amount).update(
                            balance=F("balance") - tx.amount
                        )
                        if updated != 1:
                            messages.error(request, "Баланс изменился. Внешний запрос успешен, но локальный баланс не обновился.")
                        else:
                            # refresh local object for subsequent page render
                            wallet.refresh_from_db(fields=["balance"])
                messages.success(request, "Успешно отправлено.")
            except ExternalApiError as e:
                messages.error(request, "Ошибка внешнего сервиса. Операция не отправлена.")

            return redirect("dashboard")
    else:
        form = TransactionCreateForm(client_choices=client_choices)
    return render(request, "core/transaction_form.html", {"form": form})


@login_required
def api_clients(request):
    """
    JSON endpoint for client search.
    Supports: ?referral_token=...
    """
    referral_token = (request.GET.get("referral_token") or "").strip()
    if not referral_token:
        return JsonResponse({"results": []})

    try:
        users = fetch_yildiztop_users_by_referral_token(referral_token=referral_token)
    except ExternalApiError:
        users = []

    return JsonResponse(
        {
            "results": [
                {"id": u.id, "label": u.label, "name": u.name, "email": u.email}
                for u in users
            ]
        }
    )

# Create your views here.
