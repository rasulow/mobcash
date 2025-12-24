from functools import wraps

from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect


def is_main_cashier(user) -> bool:
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name="main_cashier").exists()


def main_cashier_required(view_func):
    @login_required
    @wraps(view_func)
    def _wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if not is_main_cashier(request.user):
            return redirect("dashboard")
        return view_func(request, *args, **kwargs)

    return _wrapped


