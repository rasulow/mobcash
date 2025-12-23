from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import TransactionCreateForm
from .models import Wallet


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
    if request.method == "POST":
        form = TransactionCreateForm(request.POST)
        if form.is_valid():
            tx = form.save(commit=False)
            tx.wallet = wallet
            tx.save()
            messages.success(request, "Transaction submitted and is now pending review.")
            return redirect("dashboard")
    else:
        form = TransactionCreateForm()
    return render(request, "core/transaction_form.html", {"form": form})

# Create your views here.
