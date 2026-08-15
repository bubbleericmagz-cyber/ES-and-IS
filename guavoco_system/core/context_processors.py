"""Values that every template needs: the current user's role, the page subtitle
shown in the top bar, and the alert counts behind the notification bell.

These are read-only helpers for the interface. They do not change any business
logic - they only re-read data the pages already display.
"""

from datetime import timedelta

from django.utils import timezone

from .permissions import is_administrator

# Subtitle shown under the page title in the top bar, keyed by URL name. Keeping
# it here means the views did not have to change to gain a subtitle.
PAGE_SUBTITLES = {
    'dashboard': 'Monitor packaging, inventory, orders and product distribution',
    'product_list': 'Guavoco toothpaste products and their stock levels',
    'product_detail': 'Product details, stock by batch and recent orders',
    'product_create': 'Add a new Guavoco product or variant',
    'product_update': 'Update this product',
    'material_list': 'Tubes, caps, boxes, labels and shipping cartons',
    'material_create': 'Add a packaging material',
    'material_update': 'Update this packaging material',
    'batch_list': 'Production runs, with expiry monitoring',
    'batch_detail': 'Everything recorded against this production batch',
    'batch_create': 'Record a new production batch',
    'batch_update': 'Update this production batch',
    'packaging_list': 'Units packaged and damaged, per production batch',
    'packaging_create': 'Record a packaging session',
    'packaging_update': 'Update this packaging record',
    'inventory_list': 'Finished Guavoco stock, by product and batch',
    'inventory_adjust': 'Correct a stock figure after a physical count',
    'customer_list': 'Distributors, retailers, pharmacies and direct customers',
    'customer_detail': 'Contact details and order history',
    'customer_create': 'Add a customer or distributor',
    'customer_update': 'Update this customer',
    'order_list': 'Customer orders from Pending through to Delivered',
    'order_detail': 'Order details, stock check and shipments',
    'order_create': 'Create a new customer order',
    'order_update': 'Update this order',
    'distribution_list': 'Shipments and the orders waiting to be sent',
    'distribute_order': 'Ship an order and deduct the stock from inventory',
    'distribution_detail': 'Shipment details and the batches it used',
    'distribution_update': 'Move this shipment along its delivery stages',
    'delivery_confirm': 'Record who received the delivery',
    'report_index': 'Filterable reports, exportable to CSV',
    'packaging_report': 'Packaging sessions, quantities and efficiency',
    'inventory_report': 'Stock on hand by product, batch and status',
    'orders_report': 'Orders, quantities and sales totals',
    'distribution_report': 'Shipments and their delivery status',
    'batch_traceability': 'Follow one batch from production to the customer',
    'activity_log': 'A record of the important actions users take',
    'user_list': 'System users and their roles',
    'user_create': 'Add a system user',
}


def user_role(request):
    """Lets any template ask {% if is_admin %} without extra view code."""
    if not hasattr(request, 'user'):
        return {}

    admin = is_administrator(request.user)
    url_name = getattr(request.resolver_match, 'url_name', '') if request.resolver_match else ''

    return {
        'is_admin': admin,
        'user_role': 'Administrator' if admin else 'Staff',
        'page_subtitle': PAGE_SUBTITLES.get(url_name, ''),
    }


def alerts(request):
    """Low stock and expiring stock counts for the notification bell."""
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {}

    # Imported here so this module can be loaded before the app registry is ready.
    from .models import Inventory, PackagingMaterial, Product

    low_products = [p for p in Product.objects.filter(is_active=True) if p.is_low_stock]
    low_materials = [m for m in PackagingMaterial.objects.filter(is_active=True)
                     if m.is_low_stock]

    today = timezone.localdate()
    expiring = list(
        Inventory.objects.filter(
            quantity_available__gt=0,
            expiration_date__lte=today + timedelta(days=30),
        ).select_related('batch', 'product').order_by('expiration_date')[:5]
    )

    return {
        'alert_low_products': low_products[:5],
        'alert_low_materials': low_materials[:5],
        'alert_expiring': expiring,
        'alert_count': len(low_products) + len(low_materials) + len(expiring),
    }
