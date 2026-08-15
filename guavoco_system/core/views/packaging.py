"""Packaging records: how many units of a batch were packaged, and how many spoiled."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import PackagingRecordForm
from ..models import ActivityLog, PackagingRecord
from ..services import StockError, complete_packaging


@login_required
def packaging_list(request):
    records = PackagingRecord.objects.select_related('batch__product', 'packaging_staff')

    search = request.GET.get('q', '').strip()
    if search:
        records = records.filter(
            Q(packaging_id__icontains=search) | Q(batch__batch_number__icontains=search)
        )

    status = request.GET.get('status', '')
    if status:
        records = records.filter(status=status)

    # Overall packaging efficiency across every completed record.
    completed = PackagingRecord.objects.filter(status=PackagingRecord.STATUS_COMPLETED)
    totals = completed.aggregate(
        received=Sum('quantity_received'),
        packaged=Sum('quantity_packaged'),
        damaged=Sum('damaged_quantity'),
    )
    received = totals['received'] or 0
    packaged = totals['packaged'] or 0
    overall_efficiency = round(packaged / received * 100, 1) if received else 0

    context = {
        'page_title': 'Packaging',
        'records': records,
        'search': search,
        'status': status,
        'statuses': PackagingRecord.STATUS_CHOICES,
        'total_received': received,
        'total_packaged': packaged,
        'total_damaged': totals['damaged'] or 0,
        'overall_efficiency': overall_efficiency,
    }
    return render(request, 'packaging/packaging_list.html', context)


@login_required
def packaging_create(request):
    form = PackagingRecordForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        record = form.save()
        ActivityLog.record(
            request.user, 'Packaging Recorded',
            f'{record.packaging_id} created for batch {record.batch.batch_number}.',
        )
        messages.success(
            request,
            f'Packaging record {record.packaging_id} was saved. '
            f'Mark it as completed to move the units into inventory.',
        )
        return redirect('packaging_list')
    return render(request, 'packaging/packaging_form.html',
                  {'page_title': 'Record Packaging', 'form': form})


@login_required
def packaging_update(request, pk):
    record = get_object_or_404(PackagingRecord, pk=pk)
    if record.status == PackagingRecord.STATUS_COMPLETED:
        messages.error(
            request,
            f'{record.packaging_id} is already completed and its units are in inventory, '
            f'so it can no longer be edited.',
        )
        return redirect('packaging_list')

    form = PackagingRecordForm(request.POST or None, instance=record)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'{record.packaging_id} was updated.')
        return redirect('packaging_list')
    return render(request, 'packaging/packaging_form.html',
                  {'page_title': f'Edit {record.packaging_id}', 'form': form,
                   'record': record})


@login_required
def packaging_complete(request, pk):
    """Finish a packaging record - this is what puts stock into inventory."""
    record = get_object_or_404(PackagingRecord, pk=pk)
    try:
        complete_packaging(record, request.user)
    except StockError as error:
        messages.error(request, str(error))
    else:
        messages.success(
            request,
            f'{record.packaging_id} completed. {record.quantity_packaged} units were '
            f'added to inventory (efficiency {record.efficiency}%).',
        )
    return redirect('packaging_list')
