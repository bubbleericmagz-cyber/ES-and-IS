"""Two simple roles, built on Django's own Group model.

Administrators can manage everything. Staff can run the day-to-day work
(packaging, orders, distribution) but cannot change master data or users.
"""

from functools import wraps

from django.contrib import messages
from django.contrib.auth.models import Group
from django.shortcuts import redirect

ADMIN_GROUP = 'Administrator'
STAFF_GROUP = 'Staff'


def ensure_groups_exist():
    """Create the two role groups if they are not in the database yet."""
    for name in (ADMIN_GROUP, STAFF_GROUP):
        Group.objects.get_or_create(name=name)


def is_administrator(user):
    """Superusers always count as administrators."""
    return user.is_authenticated and (
        user.is_superuser or user.groups.filter(name=ADMIN_GROUP).exists()
    )


def administrator_required(view_func):
    """Block staff accounts from administrator-only pages."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_administrator(request.user):
            messages.error(request, 'Only administrators can open that page.')
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)

    return wrapper
