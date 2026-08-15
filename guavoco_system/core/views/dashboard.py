"""Dashboard summary cards, charts and the activity log page.

Every number here is read from the database - nothing is hardcoded.
"""

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone

from ..models import (
    ActivityLog,
    Distribution,
    Inventory,
    Order,
    PackagingMaterial,
    PackagingRecord,
    Product,
)

CHART_DAYS = 14


def daily_totals(queryset, date_field, value_field):
    """Sum a value per day for the last CHART_DAYS days.

    Returns two lists ready for Chart.js: the dates and the matching totals.
    Days with no activity still appear, as zero, so the chart has no gaps.
    """
    today = timezone.localdate()
    start = today - timedelta(days=CHART_DAYS - 1)

    rows = (
        queryset.filter(**{f'{date_field}__gte': start, f'{date_field}__lte': today})
        .values(date_field)
        .annotate(total=Sum(value_field))
    )
    totals_by_date = {row[date_field]: row['total'] or 0 for row in rows}

    labels, values = [], []
    for offset in range(CHART_DAYS):
        day = start + timedelta(days=offset)
        labels.append(day.strftime('%b %d'))
        values.append(totals_by_date.get(day, 0))
    return labels, values


@login_required
def dashboard(request):
    today = timezone.localdate()

    # --- Summary cards -----------------------------------------------------
    products = Product.objects.filter(is_active=True)
    total_stock = Inventory.objects.aggregate(total=Sum('quantity_available'))['total'] or 0
    units_packaged = PackagingRecord.objects.filter(
        status=PackagingRecord.STATUS_COMPLETED
    ).aggregate(total=Sum('quantity_packaged'))['total'] or 0

    low_stock_products = [p for p in products if p.is_low_stock]
    low_stock_materials = [m for m in PackagingMaterial.objects.filter(is_active=True)
                           if m.is_low_stock]

    stats = {
        'total_products': products.count(),
        'total_stock': total_stock,
        'units_packaged': units_packaged,
        'pending_orders': Order.objects.filter(status=Order.STATUS_PENDING).count(),
        'for_distribution': Order.objects.filter(status=Order.STATUS_READY).count(),
        'delivered_orders': Order.objects.filter(status=Order.STATUS_DELIVERED).count(),
        'low_stock_items': len(low_stock_products) + len(low_stock_materials),
    }

    # --- Chart data --------------------------------------------------------
    packaging_labels, packaging_values = daily_totals(
        PackagingRecord.objects.filter(status=PackagingRecord.STATUS_COMPLETED),
        'packaging_date', 'quantity_packaged',
    )
    distribution_labels, distribution_values = daily_totals(
        Distribution.objects.exclude(delivery_status=Distribution.STATUS_CANCELLED),
        'distribution_date', 'quantity_distributed',
    )

    inventory_rows = (
        Inventory.objects.values('product__name')
        .annotate(total=Sum('quantity_available'))
        .order_by('-total')
    )

    order_status_counts = []
    for status, _ in Order.STATUS_CHOICES:
        order_status_counts.append(Order.objects.filter(status=status).count())

    chart_data = {
        'packaging': {'labels': packaging_labels, 'values': packaging_values},
        'distribution': {'labels': distribution_labels, 'values': distribution_values},
        'inventory': {
            'labels': [row['product__name'] for row in inventory_rows],
            'values': [row['total'] or 0 for row in inventory_rows],
        },
        'orders': {
            'labels': [status for status, _ in Order.STATUS_CHOICES],
            'values': order_status_counts,
        },
    }

    # --- Warning panels ----------------------------------------------------
    expiring_soon = Inventory.objects.filter(
        quantity_available__gt=0,
        expiration_date__lte=today + timedelta(days=60),
    ).select_related('product', 'batch').order_by('expiration_date')[:10]

    context = {
        'page_title': 'Dashboard',
        'stats': stats,
        'chart_data': chart_data,
        'low_stock_products': low_stock_products,
        'low_stock_materials': low_stock_materials,
        'expiring_soon': expiring_soon,
        'recent_activities': ActivityLog.objects.select_related('user')[:8],
    }
    return render(request, 'dashboard.html', context)


@login_required
def activity_log(request):
    logs = ActivityLog.objects.select_related('user')

    search = request.GET.get('q', '').strip()
    if search:
        logs = logs.filter(action__icontains=search)

    action_filter = request.GET.get('action', '')
    if action_filter:
        logs = logs.filter(action=action_filter)

    page = Paginator(logs, 25).get_page(request.GET.get('page'))
    context = {
        'page_title': 'Activity Log',
        'page_obj': page,
        'search': search,
        'action_filter': action_filter,
        'actions': ActivityLog.objects.values_list('action', flat=True).distinct(),
    }
    return render(request, 'activity_log.html', context)
