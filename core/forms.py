from django import forms

from .models import Transaction


class TransactionCreateForm(forms.ModelForm):
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


