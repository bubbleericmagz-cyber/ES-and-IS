"""Customer orders, including the stock check before an order can be prepared."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import OrderForm
from ..models import ActivityLog, Order, Product
from ..services import available_stock


@login_required
def order_list(request):
    orders = Order.objects.select_related('customer', 'product')

    search = request.GET.get('q', '').strip()
    if search:
        orders = orders.filter(
            Q(order_number__icontains=search)
            | Q(customer__business_name__icontains=search)
        )

    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)

    product_id = request.GET.get('product', '')
    if product_id:
        orders = orders.filter(product_id=product_id)

    start = request.GET.get('start', '')
    end = request.GET.get('end', '')
    if start:
        orders = orders.filter(order_date__gte=start)
    if end:
        orders = orders.filter(order_date__lte=end)

    context = {
        'page_title': 'Orders',
        'orders': orders,
        'search': search,
        'status': status,
        'product_id': product_id,
        'start': start,
        'end': end,
        'statuses': Order.STATUS_CHOICES,
        'products': Product.objects.all(),
    }
    return render(request, 'orders/order_list.html', context)


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('customer', 'product'), pk=pk
    )
    context = {
        'page_title': order.order_number,
        'order': order,
        'stock_on_hand': available_stock(order.product),
        'distributions': order.distributions.all(),
    }
    return render(request, 'orders/order_detail.html', context)


@login_required
def order_create(request):
    form = OrderForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        order = form.save()
        ActivityLog.record(
            request.user, 'Order Created',
            f'{order.order_number}: {order.quantity} x {order.product.name} for '
            f'{order.customer.business_name}.',
        )
        messages.success(
            request,
            f'Order {order.order_number} was created. Total: PHP {order.total_amount:,.2f}.',
        )
        return redirect('order_detail', pk=order.pk)

    context = {
        'page_title': 'Create Order',
        'form': form,
        'stock_levels': {p.id: available_stock(p) for p in Product.objects.filter(is_active=True)},
    }
    return render(request, 'orders/order_form.html', context)


@login_required
def order_update(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if order.status in [Order.STATUS_DISTRIBUTED, Order.STATUS_DELIVERED]:
        messages.error(
            request,
            f'{order.order_number} has already been {order.status.lower()} and its stock '
            f'has moved, so it can no longer be edited.',
        )
        return redirect('order_detail', pk=order.pk)

    form = OrderForm(request.POST or None, instance=order)
    if request.method == 'POST' and form.is_valid():
        form.save()
        ActivityLog.record(request.user, 'Order Updated',
                           f'{order.order_number} is now {order.status}.')
        messages.success(request, f'Order {order.order_number} was updated.')
        return redirect('order_detail', pk=order.pk)

    context = {
        'page_title': f'Edit {order.order_number}',
        'form': form,
        'order': order,
        'stock_levels': {p.id: available_stock(p) for p in Product.objects.filter(is_active=True)},
    }
    return render(request, 'orders/order_form.html', context)


@login_required
def order_cancel(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if order.status in [Order.STATUS_DISTRIBUTED, Order.STATUS_DELIVERED]:
        messages.error(request, 'An order that has already shipped cannot be cancelled.')
    else:
        order.status = Order.STATUS_CANCELLED
        order.save()
        ActivityLog.record(request.user, 'Order Cancelled', f'{order.order_number} cancelled.')
        messages.success(request, f'Order {order.order_number} was cancelled.')
    return redirect('order_detail', pk=order.pk)


@login_required
def product_price(request, product_id):
    """Used by the order form to fill in the price and show live stock."""
    product = get_object_or_404(Product, pk=product_id)
    return JsonResponse({
        'unit_price': str(product.selling_price),
        'available_stock': available_stock(product),
    })
