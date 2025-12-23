from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.http import JsonResponse
from django.db import transaction as db_transaction
from django.db.models import F

from .forms import TransactionCreateForm
from .external_api import (
    ExternalApiError,
    fetch_yildiztop_users_by_referral_token,
    fetch_yildiztop_users,
    post_yildiztop_update_balance,
)
from .models import Transaction, Wallet


def home(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return redirect("login")


@login_required
def dashboard(request):
    wallet, _ = Wallet.objects.get_or_create(user=request.user)
    transactions = wallet.transactions.all()[:10]
    return render(
        request,
        "core/dashboard.html",
        {"wallet": wallet, "transactions": transactions},
    )


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
        messages.warning(
            request,
            "Client list is currently unavailable (external API). Please try again later.",
        )

    if request.method == "POST":
        form = TransactionCreateForm(request.POST, client_choices=client_choices)
        if form.is_valid():
            client_id = form.cleaned_data["client_id"]
            ext_user = user_by_id.get(str(client_id))
            if not ext_user:
                messages.error(request, "Selected client is invalid. Please try again.")
                return redirect("transaction_create")

            # Don't store a transaction if there isn't enough money.
            amount = form.cleaned_data["amount"]
            if wallet.balance is None or Decimal(wallet.balance) < amount:
                messages.warning(
                    request,
                    f"Not sending: amount {amount} is greater than your wallet balance {wallet.balance}.",
                )
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
                users = fetch_yildiztop_users_by_referral_token(token)
                u = users[0] if users else None
                current = u.balance if (u and u.balance is not None) else Decimal("0")
                tx.external_balance_before = current
                new_balance = current + tx.amount
                post_yildiztop_update_balance(token, new_balance)

                tx.external_balance_after = new_balance
                tx.external_sync_status = Transaction.ExternalSyncStatus.SYNCED
                tx.external_sync_error = ""
                tx.save()

                # Decrease our wallet balance only after external update succeeded.
                with db_transaction.atomic():
                    updated = (
                        Wallet.objects.filter(pk=wallet.pk, balance__gte=tx.amount).update(
                            balance=F("balance") - tx.amount
                        )
                    )
                    if updated != 1:
                        messages.error(
                            request,
                            "Wallet balance changed. External update succeeded but local wallet did not deduct.",
                        )
                    else:
                        # refresh local object for subsequent page render
                        wallet.refresh_from_db(fields=["balance"])
                messages.success(request, "Sent successfully.")
            except ExternalApiError as e:
                messages.error(request, "External service error. Transaction was not sent.")

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
