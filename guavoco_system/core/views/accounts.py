"""User management - administrators only."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group, User
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import UserForm
from ..models import ActivityLog
from ..permissions import ADMIN_GROUP, administrator_required, ensure_groups_exist


def role_of(user):
    if user.is_superuser or user.groups.filter(name=ADMIN_GROUP).exists():
        return 'Administrator'
    return 'Staff'


@login_required
@administrator_required
def user_list(request):
    users = User.objects.all().order_by('username')
    rows = [{'user': user, 'role': role_of(user)} for user in users]
    return render(request, 'accounts/user_list.html',
                  {'page_title': 'Users', 'rows': rows})


@login_required
@administrator_required
def user_create(request):
    ensure_groups_exist()
    form = UserForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        group = Group.objects.get(name=form.cleaned_data['role'])
        user.groups.add(group)
        ActivityLog.record(
            request.user, 'User Added',
            f'{user.username} was created as {form.cleaned_data["role"]}.',
        )
        messages.success(request, f'User "{user.username}" was created.')
        return redirect('user_list')
    return render(request, 'accounts/user_form.html',
                  {'page_title': 'Add User', 'form': form})


@login_required
@administrator_required
def user_toggle(request, pk):
    """Disable an account instead of deleting it."""
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('user_list')
    user.is_active = not user.is_active
    user.save()
    state = 'activated' if user.is_active else 'deactivated'
    messages.success(request, f'User "{user.username}" was {state}.')
    return redirect('user_list')
