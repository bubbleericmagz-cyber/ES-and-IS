"""Finished product inventory, with expiry badges and manual adjustments."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from ..forms import InventoryAdjustmentForm
from ..models import Inventory, Product
from ..permissions import administrator_required
from ..services import StockError, adjust_inventory


@login_required
def inventory_list(request):
    rows = Inventory.objects.select_related('product', 'batch')

    search = request.GET.get('q', '').strip()
    if search:
        rows = rows.filter(
            Q(batch__batch_number__icontains=search) | Q(product__name__icontains=search)
        )

    product_id = request.GET.get('product', '')
    if product_id:
        rows = rows.filter(product_id=product_id)

    # Status is a calculated property, so it is filtered in Python.
    status = request.GET.get('status', '')
    rows = list(rows)
    if status:
        rows = [row for row in rows if row.status == status]

    total_units = sum(row.quantity_available for row in rows)
    expired_units = sum(row.quantity_available for row in rows if row.is_expired)

    context = {
        'page_title': 'Inventory',
        'rows': rows,
        'search': search,
        'status': status,
        'product_id': product_id,
        'products': Product.objects.all(),
        'statuses': ['Available', 'Low Stock', 'Out of Stock', 'Expired'],
        'total_units': total_units,
        'expired_units': expired_units,
        'today': timezone.localdate(),
    }
    return render(request, 'inventory/inventory_list.html', context)


@login_required
@administrator_required
def inventory_adjust(request, pk):
    """Correct a stock figure by hand, for example after a physical stock count."""
    row = get_object_or_404(Inventory.objects.select_related('product', 'batch'), pk=pk)
    form = InventoryAdjustmentForm(request.POST or None,
                                   initial={'new_quantity': row.quantity_available})

    if request.method == 'POST' and form.is_valid():
        try:
            adjust_inventory(row, form.cleaned_data['new_quantity'],
                             form.cleaned_data['reason'], request.user)
        except StockError as error:
            messages.error(request, str(error))
        else:
            messages.success(
                request,
                f'{row.batch.batch_number} stock is now {row.quantity_available} units.',
            )
            return redirect('inventory_list')

    return render(request, 'inventory/inventory_adjust.html',
                  {'page_title': f'Adjust {row.batch.batch_number}', 'form': form,
                   'row': row})
