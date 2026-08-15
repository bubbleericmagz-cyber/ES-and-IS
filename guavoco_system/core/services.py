"""The business rules of the system, kept together in one readable place.

Every function here changes stock levels, so each one validates its inputs
first, runs inside a database transaction, and writes an activity log entry.
Problems are raised as StockError, which the views turn into a friendly
message on screen.
"""

from django.db import models, transaction
from django.utils import timezone

from .models import (
    ActivityLog,
    Distribution,
    DistributionItem,
    Inventory,
    Order,
    PackagingRecord,
    ProductionBatch,
)


class StockError(Exception):
    """Raised when an operation would break an inventory rule."""


def available_stock(product):
    """Units of a product that can actually be sold (expired batches excluded)."""
    total = Inventory.objects.filter(
        product=product, expiration_date__gte=timezone.localdate()
    ).aggregate(total=models.Sum('quantity_available'))['total']
    return total or 0


@transaction.atomic
def complete_packaging(record, user):
    """Finish a packaging record and move the packaged units into inventory.

    Steps: check the numbers, take the units out of the batch, add them to the
    finished-product inventory, then update the batch status.
    """
    if record.status == PackagingRecord.STATUS_COMPLETED:
        raise StockError(f'{record.packaging_id} is already completed.')

    batch = ProductionBatch.objects.select_for_update().get(pk=record.batch_id)

    if record.quantity_packaged + record.damaged_quantity > record.quantity_received:
        raise StockError(
            'Packaged plus damaged quantity cannot be more than the quantity received.'
        )
    if record.quantity_received > batch.quantity_available:
        raise StockError(
            f'Batch {batch.batch_number} only has {batch.quantity_available} units left, '
            f'but this record received {record.quantity_received}.'
        )

    # The whole received amount leaves the batch: some packaged, some damaged,
    # and anything left over stays as unpackaged remainder.
    batch.quantity_available -= record.quantity_received - record.remaining_quantity

    if record.quantity_packaged:
        inventory_row, _ = Inventory.objects.get_or_create(
            product=batch.product,
            batch=batch,
            defaults={
                'date_packaged': record.packaging_date,
                'expiration_date': batch.expiration_date,
                'quantity_available': 0,
            },
        )
        inventory_row.quantity_available += record.quantity_packaged
        inventory_row.date_packaged = record.packaging_date
        inventory_row.save()

    if batch.quantity_available == 0:
        batch.status = ProductionBatch.STATUS_PACKAGED
    batch.save()

    record.status = PackagingRecord.STATUS_COMPLETED
    record.save()

    ActivityLog.record(
        user,
        'Packaging Completed',
        f'{record.packaging_id}: {record.quantity_packaged} units of '
        f'{batch.product.name} added to inventory from {batch.batch_number}.',
    )
    return record


@transaction.atomic
def distribute_order(order, distribution_data, user):
    """Ship an order: take stock out of inventory and create the shipment record.

    Stock is taken first-expiry-first-out so the oldest usable batches leave
    first. Expired batches are skipped entirely, so expired product can never
    be distributed.
    """
    if not order.can_be_distributed:
        raise StockError(f'Order {order.order_number} is already {order.status.lower()}.')

    today = timezone.localdate()
    rows = list(
        Inventory.objects.select_for_update()
        .filter(product=order.product, expiration_date__gte=today, quantity_available__gt=0)
        .order_by('expiration_date', 'id')
    )
    on_hand = sum(row.quantity_available for row in rows)
    if on_hand < order.quantity:
        raise StockError(
            f'Not enough stock for {order.order_number}. '
            f'Available (non-expired): {on_hand} units, required: {order.quantity} units.'
        )

    distribution = Distribution.objects.create(
        order=order,
        distribution_date=distribution_data.get('distribution_date', today),
        quantity_distributed=order.quantity,
        delivery_method=distribution_data.get('delivery_method', 'Company Delivery'),
        tracking_number=distribution_data.get('tracking_number', ''),
        delivery_status=distribution_data.get(
            'delivery_status', Distribution.STATUS_PREPARING
        ),
        remarks=distribution_data.get('remarks', ''),
    )

    remaining = order.quantity
    for row in rows:
        if remaining == 0:
            break
        taken = min(row.quantity_available, remaining)
        row.quantity_available -= taken
        row.save()
        DistributionItem.objects.create(
            distribution=distribution, batch=row.batch, quantity=taken
        )
        remaining -= taken

    order.status = Order.STATUS_DISTRIBUTED
    order.save()

    ActivityLog.record(
        user,
        'Order Distributed',
        f'{order.order_number}: {order.quantity} units sent to '
        f'{order.customer.business_name} as {distribution.distribution_number}.',
    )
    return distribution


@transaction.atomic
def confirm_delivery(distribution, confirmation, user):
    """Mark a shipment - and its order - as delivered."""
    if distribution.delivery_status == Distribution.STATUS_CANCELLED:
        raise StockError('A cancelled distribution cannot be marked as delivered.')

    confirmation.distribution = distribution
    confirmation.save()

    distribution.delivery_status = Distribution.STATUS_DELIVERED
    distribution.save()

    order = distribution.order
    order.status = Order.STATUS_DELIVERED
    order.save()

    ActivityLog.record(
        user,
        'Order Delivered',
        f'{order.order_number} received by {confirmation.receiver_name} '
        f'on {confirmation.delivery_date}.',
    )
    return confirmation


@transaction.atomic
def adjust_inventory(inventory_row, new_quantity, reason, user):
    """Manually correct an inventory row. Stock can never go below zero."""
    if new_quantity < 0:
        raise StockError('Inventory quantity cannot be negative.')

    old_quantity = inventory_row.quantity_available
    inventory_row.quantity_available = new_quantity
    inventory_row.save()

    ActivityLog.record(
        user,
        'Inventory Updated',
        f'{inventory_row.batch.batch_number}: {old_quantity} -> {new_quantity} units. '
        f'Reason: {reason or "not given"}.',
    )
    return inventory_row
