"""Customers and distributors who receive Guavoco products."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import CustomerForm
from ..models import ActivityLog, Customer
from ..permissions import administrator_required


@login_required
def customer_list(request):
    customers = Customer.objects.all()

    search = request.GET.get('q', '').strip()
    if search:
        customers = customers.filter(
            Q(business_name__icontains=search)
            | Q(contact_person__icontains=search)
            | Q(customer_id__icontains=search)
        )

    customer_type = request.GET.get('type', '')
    if customer_type:
        customers = customers.filter(customer_type=customer_type)

    status = request.GET.get('status', '')
    if status == 'active':
        customers = customers.filter(is_active=True)
    elif status == 'inactive':
        customers = customers.filter(is_active=False)

    context = {
        'page_title': 'Customers / Distributors',
        'customers': customers,
        'search': search,
        'customer_type': customer_type,
        'status': status,
        'types': Customer.TYPE_CHOICES,
    }
    return render(request, 'customers/customer_list.html', context)


@login_required
def customer_detail(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    context = {
        'page_title': customer.business_name,
        'customer': customer,
        'orders': customer.orders.select_related('product'),
    }
    return render(request, 'customers/customer_detail.html', context)


@login_required
@administrator_required
def customer_create(request):
    form = CustomerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        customer = form.save()
        ActivityLog.record(request.user, 'Customer Added',
                           f'{customer.business_name} ({customer.customer_type}) was added.')
        messages.success(request, f'"{customer.business_name}" was added.')
        return redirect('customer_list')
    return render(request, 'customers/customer_form.html',
                  {'page_title': 'Add Customer / Distributor', 'form': form})


@login_required
@administrator_required
def customer_update(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    form = CustomerForm(request.POST or None, instance=customer)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'"{customer.business_name}" was updated.')
        return redirect('customer_list')
    return render(request, 'customers/customer_form.html',
                  {'page_title': f'Edit {customer.business_name}', 'form': form})


@login_required
@administrator_required
def customer_toggle(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    customer.is_active = not customer.is_active
    customer.save()
    state = 'activated' if customer.is_active else 'deactivated'
    messages.success(request, f'"{customer.business_name}" was {state}.')
    return redirect('customer_list')
