"""Database models for the Guavoco Packaging & Distribution Management System.

The flow the models describe is:

    Product -> ProductionBatch -> PackagingRecord -> Inventory
            -> Order -> Distribution -> DeliveryConfirmation
"""

from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


def next_reference(model, field_name, prefix):
    """Build the next reference number for a model, e.g. 'GVC-BATCH-0001'.

    All of our auto-generated IDs share this format, so they all share this
    one helper instead of repeating the same logic in every model.
    """
    last = model.objects.order_by('-id').first()
    if last is None:
        next_number = 1
    else:
        # Take the digits after the final dash and add one.
        last_value = getattr(last, field_name) or ''
        try:
            next_number = int(last_value.split('-')[-1]) + 1
        except ValueError:
            next_number = model.objects.count() + 1
    return f'{prefix}-{next_number:04d}'


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

class Product(models.Model):
    """A Guavoco product, e.g. the guava and coconut toothpaste."""

    name = models.CharField(max_length=100)
    sku = models.CharField('SKU', max_length=50, unique=True)
    description = models.TextField(blank=True)
    size = models.CharField('Product size', max_length=50, help_text='For example: 100g tube')
    selling_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    reorder_level = models.PositiveIntegerField(
        default=100, help_text='Warn when available stock falls to this level.'
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.sku})'

    @property
    def current_stock(self):
        """Total units on hand, summed from the inventory rows.

        This is calculated instead of stored so it can never disagree with
        the inventory table.
        """
        total = self.inventory_rows.aggregate(total=models.Sum('quantity_available'))['total']
        return total or 0

    @property
    def sellable_stock(self):
        """Stock that may actually be sold - expired batches are excluded."""
        total = self.inventory_rows.filter(
            expiration_date__gte=timezone.localdate()
        ).aggregate(total=models.Sum('quantity_available'))['total']
        return total or 0

    @property
    def is_low_stock(self):
        return self.current_stock <= self.reorder_level

    @property
    def status_label(self):
        if not self.is_active:
            return 'Inactive'
        if self.current_stock == 0:
            return 'Out of Stock'
        if self.is_low_stock:
            return 'Low Stock'
        return 'Available'


# ---------------------------------------------------------------------------
# Production
# ---------------------------------------------------------------------------

def expiry_state_for(expiration_date):
    """Classify an expiration date so templates can show a coloured badge."""
    if expiration_date is None:
        return 'Safe'
    days_left = (expiration_date - timezone.localdate()).days
    if days_left < 0:
        return 'Expired'
    if days_left <= 30:
        return 'Expiring in 30 Days'
    if days_left <= 60:
        return 'Expiring in 60 Days'
    return 'Safe'


class ProductionBatch(models.Model):
    """One production run of a product."""

    STATUS_PRODUCED = 'Produced'
    STATUS_READY = 'Ready for Packaging'
    STATUS_PACKAGED = 'Packaged'
    STATUS_COMPLETED = 'Completed'
    STATUS_CHOICES = [
        (STATUS_PRODUCED, STATUS_PRODUCED),
        (STATUS_READY, STATUS_READY),
        (STATUS_PACKAGED, STATUS_PACKAGED),
        (STATUS_COMPLETED, STATUS_COMPLETED),
    ]

    batch_number = models.CharField(max_length=30, unique=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='batches')
    production_date = models.DateField(default=timezone.localdate)
    expiration_date = models.DateField()
    quantity_produced = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    quantity_available = models.PositiveIntegerField(
        default=0, help_text='Units from this batch that have not been packaged yet.'
    )
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PRODUCED)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-production_date', '-id']
        verbose_name_plural = 'Production batches'

    def __str__(self):
        return self.batch_number

    def save(self, *args, **kwargs):
        if not self.batch_number:
            self.batch_number = next_reference(ProductionBatch, 'batch_number', 'GVC-BATCH')
        super().save(*args, **kwargs)

    @property
    def expiry_state(self):
        return expiry_state_for(self.expiration_date)

    @property
    def is_expired(self):
        return self.expiration_date < timezone.localdate()

    @property
    def quantity_packaged(self):
        total = self.packaging_records.filter(
            status=PackagingRecord.STATUS_COMPLETED
        ).aggregate(total=models.Sum('quantity_packaged'))['total']
        return total or 0

    @property
    def quantity_damaged(self):
        total = self.packaging_records.filter(
            status=PackagingRecord.STATUS_COMPLETED
        ).aggregate(total=models.Sum('damaged_quantity'))['total']
        return total or 0


# ---------------------------------------------------------------------------
# Packaging
# ---------------------------------------------------------------------------

class PackagingRecord(models.Model):
    """Records how many units of a batch were successfully packaged."""

    STATUS_PENDING = 'Pending'
    STATUS_IN_PROGRESS = 'In Progress'
    STATUS_COMPLETED = 'Completed'
    STATUS_CHOICES = [
        (STATUS_PENDING, STATUS_PENDING),
        (STATUS_IN_PROGRESS, STATUS_IN_PROGRESS),
        (STATUS_COMPLETED, STATUS_COMPLETED),
    ]

    packaging_id = models.CharField(max_length=30, unique=True, blank=True)
    batch = models.ForeignKey(
        ProductionBatch, on_delete=models.CASCADE, related_name='packaging_records'
    )
    packaging_date = models.DateField(default=timezone.localdate)
    quantity_received = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    quantity_packaged = models.PositiveIntegerField(default=0)
    damaged_quantity = models.PositiveIntegerField(default=0)
    remaining_quantity = models.PositiveIntegerField(default=0)
    packaging_staff = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='packaging_records'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-packaging_date', '-id']

    def __str__(self):
        return self.packaging_id

    def save(self, *args, **kwargs):
        if not self.packaging_id:
            self.packaging_id = next_reference(PackagingRecord, 'packaging_id', 'GVC-PKG')
        # Remaining = received - packaged - damaged, never below zero.
        remaining = self.quantity_received - self.quantity_packaged - self.damaged_quantity
        self.remaining_quantity = max(remaining, 0)
        super().save(*args, **kwargs)

    @property
    def efficiency(self):
        """Packaging efficiency as a percentage: packaged / received x 100."""
        if not self.quantity_received:
            return 0
        return round(self.quantity_packaged / self.quantity_received * 100, 1)


class PackagingMaterial(models.Model):
    """Consumables used during packaging: tubes, caps, boxes, labels, cartons."""

    material_id = models.CharField(max_length=30, unique=True, blank=True)
    name = models.CharField(max_length=100)
    quantity_available = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=100)
    unit = models.CharField(max_length=30, default='pieces')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.material_id:
            self.material_id = next_reference(PackagingMaterial, 'material_id', 'GVC-MAT')
        super().save(*args, **kwargs)

    @property
    def is_low_stock(self):
        return self.quantity_available <= self.reorder_level

    @property
    def status_label(self):
        return 'Low Stock' if self.is_low_stock else 'Normal Stock'


# ---------------------------------------------------------------------------
# Finished product inventory
# ---------------------------------------------------------------------------

class Inventory(models.Model):
    """Finished, packaged stock - one row per product/batch combination."""

    LOW_STOCK_LEVEL = 100

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='inventory_rows')
    batch = models.ForeignKey(
        ProductionBatch, on_delete=models.CASCADE, related_name='inventory_rows'
    )
    quantity_available = models.PositiveIntegerField(default=0)
    date_packaged = models.DateField(default=timezone.localdate)
    expiration_date = models.DateField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['expiration_date', 'id']
        unique_together = ('product', 'batch')
        verbose_name_plural = 'Inventory'

    def __str__(self):
        return f'{self.product.name} - {self.batch.batch_number}'

    @property
    def is_expired(self):
        return self.expiration_date < timezone.localdate()

    @property
    def expiry_state(self):
        return expiry_state_for(self.expiration_date)

    @property
    def status(self):
        if self.is_expired:
            return 'Expired'
        if self.quantity_available == 0:
            return 'Out of Stock'
        if self.quantity_available <= self.LOW_STOCK_LEVEL:
            return 'Low Stock'
        return 'Available'


# ---------------------------------------------------------------------------
# Customers and orders
# ---------------------------------------------------------------------------

class Customer(models.Model):
    """A distributor, retailer or direct customer receiving Guavoco products."""

    TYPE_CHOICES = [
        ('Distributor', 'Distributor'),
        ('Retailer', 'Retailer'),
        ('Pharmacy', 'Pharmacy'),
        ('Grocery Store', 'Grocery Store'),
        ('Direct Customer', 'Direct Customer'),
    ]

    customer_id = models.CharField(max_length=30, unique=True, blank=True)
    business_name = models.CharField(max_length=150)
    contact_person = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=30)
    email = models.EmailField(blank=True)
    address = models.TextField(blank=True)
    customer_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default='Distributor')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['business_name']

    def __str__(self):
        return self.business_name

    def save(self, *args, **kwargs):
        if not self.customer_id:
            self.customer_id = next_reference(Customer, 'customer_id', 'GVC-CUS')
        super().save(*args, **kwargs)

    @property
    def status_label(self):
        return 'Active' if self.is_active else 'Inactive'


class Order(models.Model):
    """An order placed by a customer or distributor."""

    STATUS_PENDING = 'Pending'
    STATUS_PROCESSING = 'Processing'
    STATUS_READY = 'Ready for Distribution'
    STATUS_DISTRIBUTED = 'Distributed'
    STATUS_DELIVERED = 'Delivered'
    STATUS_CANCELLED = 'Cancelled'
    STATUS_CHOICES = [
        (STATUS_PENDING, STATUS_PENDING),
        (STATUS_PROCESSING, STATUS_PROCESSING),
        (STATUS_READY, STATUS_READY),
        (STATUS_DISTRIBUTED, STATUS_DISTRIBUTED),
        (STATUS_DELIVERED, STATUS_DELIVERED),
        (STATUS_CANCELLED, STATUS_CANCELLED),
    ]
    # Once an order reaches one of these states its stock has already moved.
    CLOSED_STATUSES = [STATUS_DISTRIBUTED, STATUS_DELIVERED, STATUS_CANCELLED]

    order_number = models.CharField(max_length=30, unique=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name='orders')
    order_date = models.DateField(default=timezone.localdate)
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name='orders')
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(0)]
    )
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=STATUS_PENDING)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-order_date', '-id']

    def __str__(self):
        return self.order_number

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = next_reference(Order, 'order_number', 'GVC-ORD')
        self.total_amount = self.quantity * self.unit_price
        super().save(*args, **kwargs)

    @property
    def can_be_distributed(self):
        return self.status not in self.CLOSED_STATUSES


# ---------------------------------------------------------------------------
# Distribution and delivery
# ---------------------------------------------------------------------------

class Distribution(models.Model):
    """A shipment that fulfils an order."""

    METHOD_CHOICES = [
        ('Company Delivery', 'Company Delivery'),
        ('Courier', 'Courier'),
        ('Customer Pickup', 'Customer Pickup'),
    ]

    STATUS_PREPARING = 'Preparing'
    STATUS_FOR_DELIVERY = 'For Delivery'
    STATUS_IN_TRANSIT = 'In Transit'
    STATUS_DELIVERED = 'Delivered'
    STATUS_CANCELLED = 'Cancelled'
    STATUS_CHOICES = [
        (STATUS_PREPARING, STATUS_PREPARING),
        (STATUS_FOR_DELIVERY, STATUS_FOR_DELIVERY),
        (STATUS_IN_TRANSIT, STATUS_IN_TRANSIT),
        (STATUS_DELIVERED, STATUS_DELIVERED),
        (STATUS_CANCELLED, STATUS_CANCELLED),
    ]

    distribution_number = models.CharField(max_length=30, unique=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='distributions')
    distribution_date = models.DateField(default=timezone.localdate)
    quantity_distributed = models.PositiveIntegerField(default=0)
    delivery_method = models.CharField(
        max_length=30, choices=METHOD_CHOICES, default='Company Delivery'
    )
    tracking_number = models.CharField(max_length=50, blank=True)
    delivery_status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PREPARING
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-distribution_date', '-id']

    def __str__(self):
        return self.distribution_number

    def save(self, *args, **kwargs):
        if not self.distribution_number:
            self.distribution_number = next_reference(
                Distribution, 'distribution_number', 'GVC-DIST'
            )
        super().save(*args, **kwargs)

    @property
    def customer(self):
        return self.order.customer


class DistributionItem(models.Model):
    """Which batch each shipped unit came from.

    One order can be filled from more than one batch, so we store a row per
    batch used. This is what makes the batch traceability page possible.
    """

    distribution = models.ForeignKey(
        Distribution, on_delete=models.CASCADE, related_name='items'
    )
    batch = models.ForeignKey(
        ProductionBatch, on_delete=models.PROTECT, related_name='distribution_items'
    )
    quantity = models.PositiveIntegerField()

    def __str__(self):
        return f'{self.batch.batch_number} x {self.quantity}'


class DeliveryConfirmation(models.Model):
    """Proof that a shipment arrived."""

    distribution = models.OneToOneField(
        Distribution, on_delete=models.CASCADE, related_name='confirmation'
    )
    delivery_date = models.DateField(default=timezone.localdate)
    receiver_name = models.CharField(max_length=100)
    delivered_quantity = models.PositiveIntegerField()
    remarks = models.TextField(blank=True)
    confirmed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-delivery_date', '-id']

    def __str__(self):
        return f'Delivery for {self.distribution.distribution_number}'


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------

class ActivityLog(models.Model):
    """A simple audit trail of the important things users do."""

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=60)
    description = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ['-timestamp', '-id']

    def __str__(self):
        return f'{self.action} - {self.timestamp:%Y-%m-%d %H:%M}'

    @staticmethod
    def record(user, action, description=''):
        """Shortcut used across the app to write a log entry."""
        return ActivityLog.objects.create(
            user=user if user and user.is_authenticated else None,
            action=action,
            description=description,
        )
