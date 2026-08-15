"""Distribution (shipping) and delivery confirmation."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import (
    DeliveryConfirmationForm,
    DistributionForm,
    DistributionUpdateForm,
)
from ..models import ActivityLog, Distribution, Order
from ..services import StockError, available_stock, confirm_delivery, distribute_order


@login_required
def distribution_list(request):
    distributions = Distribution.objects.select_related('order__customer', 'order__product')

    search = request.GET.get('q', '').strip()
    if search:
        distributions = distributions.filter(
            Q(distribution_number__icontains=search)
            | Q(order__order_number__icontains=search)
            | Q(order__customer__business_name__icontains=search)
        )

    status = request.GET.get('status', '')
    if status:
        distributions = distributions.filter(delivery_status=status)

    # Orders that are waiting to be shipped, shown as a to-do list at the top.
    ready_orders = Order.objects.filter(
        status__in=[Order.STATUS_PENDING, Order.STATUS_PROCESSING, Order.STATUS_READY]
    ).select_related('customer', 'product')

    context = {
        'page_title': 'Distribution',
        'distributions': distributions,
        'ready_orders': ready_orders,
        'search': search,
        'status': status,
        'statuses': Distribution.STATUS_CHOICES,
    }
    return render(request, 'distribution/distribution_list.html', context)


@login_required
def distribute_order_view(request, order_id):
    """Ship an order: this is the step that deducts stock from inventory."""
    order = get_object_or_404(
        Order.objects.select_related('customer', 'product'), pk=order_id
    )
    if not order.can_be_distributed:
        messages.error(request, f'Order {order.order_number} is already {order.status.lower()}.')
        return redirect('order_detail', pk=order.pk)

    form = DistributionForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            shipment = distribute_order(order, form.cleaned_data, request.user)
        except StockError as error:
            messages.error(request, str(error))
        else:
            messages.success(
                request,
                f'{shipment.distribution_number} created. {shipment.quantity_distributed} '
                f'units were deducted from inventory.',
            )
            return redirect('distribution_detail', pk=shipment.pk)

    context = {
        'page_title': f'Distribute {order.order_number}',
        'form': form,
        'order': order,
        'stock_on_hand': available_stock(order.product),
    }
    return render(request, 'distribution/distribute_form.html', context)


@login_required
def distribution_detail(request, pk):
    shipment = get_object_or_404(
        Distribution.objects.select_related('order__customer', 'order__product'), pk=pk
    )
    context = {
        'page_title': shipment.distribution_number,
        'shipment': shipment,
        'items': shipment.items.select_related('batch'),
        'confirmation': getattr(shipment, 'confirmation', None),
    }
    return render(request, 'distribution/distribution_detail.html', context)


@login_required
def distribution_update(request, pk):
    """Move a shipment along its delivery statuses."""
    shipment = get_object_or_404(Distribution, pk=pk)
    form = DistributionUpdateForm(request.POST or None, instance=shipment)
    if request.method == 'POST' and form.is_valid():
        form.save()
        ActivityLog.record(
            request.user, 'Distribution Updated',
            f'{shipment.distribution_number} is now {shipment.delivery_status}.',
        )
        messages.success(request, f'{shipment.distribution_number} was updated.')
        return redirect('distribution_detail', pk=shipment.pk)
    return render(request, 'distribution/distribution_form.html',
                  {'page_title': f'Update {shipment.distribution_number}',
                   'form': form, 'shipment': shipment})


@login_required
def delivery_confirm(request, pk):
    """Record who received the delivery, and mark the order as Delivered."""
    shipment = get_object_or_404(
        Distribution.objects.select_related('order__customer'), pk=pk
    )
    if hasattr(shipment, 'confirmation'):
        messages.info(request, f'{shipment.distribution_number} is already confirmed.')
        return redirect('distribution_detail', pk=shipment.pk)

    form = DeliveryConfirmationForm(request.POST or None, distribution=shipment)
    if request.method == 'POST' and form.is_valid():
        try:
            confirm_delivery(shipment, form.save(commit=False), request.user)
        except StockError as error:
            messages.error(request, str(error))
        else:
            messages.success(
                request,
                f'{shipment.order.order_number} is now marked as Delivered.',
            )
            return redirect('distribution_detail', pk=shipment.pk)

    return render(request, 'distribution/delivery_form.html',
                  {'page_title': f'Confirm Delivery - {shipment.distribution_number}',
                   'form': form, 'shipment': shipment})
