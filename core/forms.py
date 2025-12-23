from django import forms

from .models import Transaction


class TransactionCreateForm(forms.ModelForm):
    client_id = forms.ChoiceField(
        choices=[],
        required=True,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Client",
    )

    class Meta:
        model = Transaction
        fields = ["amount", "note"]
        widgets = {
            "amount": forms.NumberInput(
                attrs={"class": "form-control", "step": "0.01", "min": "0"}
            ),
            "note": forms.TextInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, client_choices: list[tuple[str, str]] | None = None, **kwargs):
        super().__init__(*args, **kwargs)
        choices = client_choices or []
        self.fields["client_id"].choices = choices
        if not choices:
            self.fields["client_id"].required = False
            self.fields["client_id"].widget.attrs["disabled"] = True


