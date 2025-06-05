from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_admin:
            messages.error(request, 'У вас нет доступа к этой странице.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper


def support_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not (request.user.is_support or request.user.is_admin):
            messages.error(request, 'У вас нет доступа к этой странице.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper