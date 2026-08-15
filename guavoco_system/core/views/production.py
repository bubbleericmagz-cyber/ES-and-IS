"""Production batch management."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import ProductionBatchForm
from ..models import ActivityLog, Product, ProductionBatch
from ..permissions import administrator_required


@login_required
def batch_list(request):
    batches = ProductionBatch.objects.select_related('product')

    search = request.GET.get('q', '').strip()
    if search:
        batches = batches.filter(batch_number__icontains=search)

    status = request.GET.get('status', '')
    if status:
        batches = batches.filter(status=status)

    product_id = request.GET.get('product', '')
    if product_id:
        batches = batches.filter(product_id=product_id)

    context = {
        'page_title': 'Production Batches',
        'batches': batches,
        'search': search,
        'status': status,
        'product_id': product_id,
        'statuses': ProductionBatch.STATUS_CHOICES,
        'products': Product.objects.all(),
    }
    return render(request, 'production/batch_list.html', context)


@login_required
def batch_detail(request, pk):
    batch = get_object_or_404(
        ProductionBatch.objects.select_related('product'), pk=pk
    )
    context = {
        'page_title': batch.batch_number,
        'batch': batch,
        'packaging_records': batch.packaging_records.all(),
        'inventory_rows': batch.inventory_rows.all(),
    }
    return render(request, 'production/batch_detail.html', context)


@login_required
@administrator_required
def batch_create(request):
    form = ProductionBatchForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        batch = form.save()
        ActivityLog.record(
            request.user, 'Batch Created',
            f'{batch.batch_number}: {batch.quantity_produced} units of {batch.product.name}.',
        )
        messages.success(request, f'Batch {batch.batch_number} was created.')
        return redirect('batch_detail', pk=batch.pk)
    return render(request, 'production/batch_form.html',
                  {'page_title': 'Add Production Batch', 'form': form})


@login_required
@administrator_required
def batch_update(request, pk):
    batch = get_object_or_404(ProductionBatch, pk=pk)
    form = ProductionBatchForm(request.POST or None, instance=batch)
    if request.method == 'POST' and form.is_valid():
        form.save()
        ActivityLog.record(request.user, 'Batch Updated', f'{batch.batch_number} was edited.')
        messages.success(request, f'Batch {batch.batch_number} was updated.')
        return redirect('batch_detail', pk=batch.pk)
    return render(request, 'production/batch_form.html',
                  {'page_title': f'Edit {batch.batch_number}', 'form': form, 'batch': batch})
