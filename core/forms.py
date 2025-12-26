from django import forms

from django.contrib.auth import get_user_model

from .models import Transaction, Wallet

User = get_user_model()


class TransactionCreateForm(forms.ModelForm):
    client_id = forms.ChoiceField(
        choices=[],
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Клиент",
    )

    class Meta:
        model = Transaction
        fields = ["type", "amount", "note"]
        widgets = {
            "type": forms.Select(attrs={"class": "form-select"}),
            "amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "note": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, client_choices: list[tuple[str, str]] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        # Default selection for new transactions
        self.fields["type"].initial = Transaction.Type.DEPOSIT
        choices = client_choices or []
        self.fields["client_id"].choices = choices
        if not choices:
            self.fields["client_id"].required = False
            self.fields["client_id"].widget.attrs["disabled"] = True


class CashierDepositForm(forms.Form):
    to_user = forms.ModelChoiceField(
        queryset=User.objects.all().order_by("username"),
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Пользователь",
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=0.01,
        widget=forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "min": "0.01"}),
        label="Сумма",
    )


