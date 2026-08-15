"""Reports, CSV export and the batch traceability page.

Each report builds a queryset from the same filter parameters. If the URL has
?export=csv the same rows are written out as a CSV file instead of a page.
"""

import csv

from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render

from ..models import (
    Distribution,
    DistributionItem,
    Inventory,
    Order,
    PackagingRecord,
    Product,
    ProductionBatch,
)


def read_filters(request):
    """Pull the four shared filter values out of the query string."""
    return {
        'start': request.GET.get('start', ''),
        'end': request.GET.get('end', ''),
        'product': request.GET.get('product', ''),
        'status': request.GET.get('status', ''),
    }


def apply_date_range(queryset, date_field, filters):
    if filters['start']:
        queryset = queryset.filter(**{f'{date_field}__gte': filters['start']})
    if filters['end']:
        queryset = queryset.filter(**{f'{date_field}__lte': filters['end']})
    return queryset


def csv_response(filename, header, rows):
    """Stream a list of rows as a downloadable CSV file."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    writer = csv.writer(response)
    writer.writerow(header)
    writer.writerows(rows)
    return response


def base_context(title, filters, status_choices=None):
    """The context every report page needs: its title, filters and dropdowns."""
    return {
        'page_title': title,
        'filters': filters,
        'products': Product.objects.all(),
        'status_choices': status_choices or [],
    }


@login_required
def report_index(request):
    return render(request, 'reports/report_index.html', {'page_title': 'Reports'})


@login_required
def packaging_report(request):
    filters = read_filters(request)
    records = PackagingRecord.objects.select_related('batch__product')
    records = apply_date_range(records, 'packaging_date', filters)
    if filters['product']:
        records = records.filter(batch__product_id=filters['product'])
    if filters['status']:
        records = records.filter(status=filters['status'])

    if request.GET.get('export') == 'csv':
        return csv_response(
            'guavoco_packaging_report.csv',
            ['Date', 'Packaging ID', 'Batch', 'Product', 'Quantity Received',
             'Quantity Packaged', 'Damaged Quantity', 'Efficiency %', 'Status'],
            [[r.packaging_date, r.packaging_id, r.batch.batch_number, r.batch.product.name,
              r.quantity_received, r.quantity_packaged, r.damaged_quantity,
              r.efficiency, r.status] for r in records],
        )

    totals = records.aggregate(
        received=Sum('quantity_received'),
        packaged=Sum('quantity_packaged'),
        damaged=Sum('damaged_quantity'),
    )
    context = base_context('Packaging Report', filters,
                           PackagingRecord.STATUS_CHOICES)
    context.update({'records': records, 'totals': totals})
    return render(request, 'reports/packaging_report.html', context)


@login_required
def inventory_report(request):
    filters = read_filters(request)
    rows = Inventory.objects.select_related('product', 'batch')
    rows = apply_date_range(rows, 'date_packaged', filters)
    if filters['product']:
        rows = rows.filter(product_id=filters['product'])

    # Inventory status is calculated, so it is filtered after the query runs.
    rows = list(rows)
    if filters['status']:
        rows = [row for row in rows if row.status == filters['status']]

    if request.GET.get('export') == 'csv':
        return csv_response(
            'guavoco_inventory_report.csv',
            ['Product', 'Batch', 'Available Stock', 'Date Packaged',
             'Expiration Date', 'Status'],
            [[r.product.name, r.batch.batch_number, r.quantity_available,
              r.date_packaged, r.expiration_date, r.status] for r in rows],
        )

    context = base_context('Inventory Report', filters,
                           [(s, s) for s in
                            ['Available', 'Low Stock', 'Out of Stock', 'Expired']])
    context.update({
        'rows': rows,
        'total_units': sum(r.quantity_available for r in rows),
    })
    return render(request, 'reports/inventory_report.html', context)


@login_required
def orders_report(request):
    filters = read_filters(request)
    orders = Order.objects.select_related('customer', 'product')
    orders = apply_date_range(orders, 'order_date', filters)
    if filters['product']:
        orders = orders.filter(product_id=filters['product'])
    if filters['status']:
        orders = orders.filter(status=filters['status'])

    if request.GET.get('export') == 'csv':
        return csv_response(
            'guavoco_orders_report.csv',
            ['Order Number', 'Customer', 'Order Date', 'Product', 'Quantity',
             'Unit Price', 'Total Amount', 'Status'],
            [[o.order_number, o.customer.business_name, o.order_date, o.product.name,
              o.quantity, o.unit_price, o.total_amount, o.status] for o in orders],
        )

    totals = orders.aggregate(quantity=Sum('quantity'), amount=Sum('total_amount'))
    context = base_context('Orders Report', filters, Order.STATUS_CHOICES)
    context.update({'orders': orders, 'totals': totals})
    return render(request, 'reports/orders_report.html', context)


@login_required
def distribution_report(request):
    filters = read_filters(request)
    shipments = Distribution.objects.select_related('order__customer', 'order__product')
    shipments = apply_date_range(shipments, 'distribution_date', filters)
    if filters['product']:
        shipments = shipments.filter(order__product_id=filters['product'])
    if filters['status']:
        shipments = shipments.filter(delivery_status=filters['status'])

    if request.GET.get('export') == 'csv':
        return csv_response(
            'guavoco_distribution_report.csv',
            ['Distribution Number', 'Order Number', 'Customer', 'Quantity',
             'Distribution Date', 'Delivery Method', 'Delivery Status'],
            [[d.distribution_number, d.order.order_number, d.order.customer.business_name,
              d.quantity_distributed, d.distribution_date, d.delivery_method,
              d.delivery_status] for d in shipments],
        )

    totals = shipments.aggregate(quantity=Sum('quantity_distributed'))
    context = base_context('Distribution Report', filters,
                           Distribution.STATUS_CHOICES)
    context.update({'shipments': shipments, 'totals': totals})
    return render(request, 'reports/distribution_report.html', context)


@login_required
def batch_traceability(request):
    """Follow one batch all the way from production to the customers who got it."""
    batch_number = request.GET.get('batch_number', '').strip()
    context = {
        'page_title': 'Batch Traceability',
        'batch_number': batch_number,
        'all_batches': ProductionBatch.objects.values_list('batch_number', flat=True),
    }

    if not batch_number:
        return render(request, 'reports/traceability.html', context)

    batch = ProductionBatch.objects.filter(batch_number__iexact=batch_number).first()
    if batch is None:
        context['not_found'] = True
        return render(request, 'reports/traceability.html', context)

    items = (
        DistributionItem.objects.filter(batch=batch)
        .select_related('distribution__order__customer', 'distribution__order__product')
        .order_by('distribution__distribution_date')
    )
    remaining = Inventory.objects.filter(batch=batch).aggregate(
        total=Sum('quantity_available')
    )['total'] or 0

    context.update({
        'batch': batch,
        'packaging_records': batch.packaging_records.all(),
        'remaining_inventory': remaining,
        'items': items,
        'shipped_total': sum(item.quantity for item in items),
        'customers': sorted({item.distribution.order.customer.business_name
                             for item in items}),
    })
    return render(request, 'reports/traceability.html', context)
