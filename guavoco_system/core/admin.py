"""Register the models so they can also be inspected from Django's admin site."""

from django.contrib import admin

from .models import (
    ActivityLog,
    Customer,
    DeliveryConfirmation,
    Distribution,
    DistributionItem,
    Inventory,
    Order,
    PackagingMaterial,
    PackagingRecord,
    ProductionBatch,
    Product,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'sku', 'size', 'selling_price', 'reorder_level', 'is_active']
    search_fields = ['name', 'sku']


@admin.register(ProductionBatch)
class ProductionBatchAdmin(admin.ModelAdmin):
    list_display = ['batch_number', 'product', 'production_date', 'expiration_date',
                    'quantity_produced', 'quantity_available', 'status']
    search_fields = ['batch_number']
    list_filter = ['status']


@admin.register(PackagingRecord)
class PackagingRecordAdmin(admin.ModelAdmin):
    list_display = ['packaging_id', 'batch', 'packaging_date', 'quantity_received',
                    'quantity_packaged', 'damaged_quantity', 'status']
    search_fields = ['packaging_id', 'batch__batch_number']
    list_filter = ['status']


@admin.register(PackagingMaterial)
class PackagingMaterialAdmin(admin.ModelAdmin):
    list_display = ['material_id', 'name', 'quantity_available', 'reorder_level', 'unit']
    search_fields = ['name']


@admin.register(Inventory)
class InventoryAdmin(admin.ModelAdmin):
    list_display = ['product', 'batch', 'quantity_available', 'date_packaged',
                    'expiration_date']
    search_fields = ['batch__batch_number', 'product__name']


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['customer_id', 'business_name', 'contact_person', 'customer_type',
                    'is_active']
    search_fields = ['business_name', 'contact_person']
    list_filter = ['customer_type', 'is_active']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer', 'product', 'quantity', 'total_amount',
                    'order_date', 'status']
    search_fields = ['order_number', 'customer__business_name']
    list_filter = ['status']


class DistributionItemInline(admin.TabularInline):
    model = DistributionItem
    extra = 0


@admin.register(Distribution)
class DistributionAdmin(admin.ModelAdmin):
    list_display = ['distribution_number', 'order', 'distribution_date',
                    'quantity_distributed', 'delivery_method', 'delivery_status']
    search_fields = ['distribution_number', 'order__order_number']
    list_filter = ['delivery_status', 'delivery_method']
    inlines = [DistributionItemInline]


@admin.register(DeliveryConfirmation)
class DeliveryConfirmationAdmin(admin.ModelAdmin):
    list_display = ['distribution', 'delivery_date', 'receiver_name', 'delivered_quantity']


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ['timestamp', 'user', 'action', 'description']
    list_filter = ['action']
