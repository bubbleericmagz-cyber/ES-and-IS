"""Django forms used for every data entry screen in the system.

BootstrapFormMixin adds the Bootstrap CSS classes so we do not have to repeat
widget attributes on every single field.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.utils import timezone

from .models import (
    Customer,
    DeliveryConfirmation,
    Distribution,
    Order,
    PackagingMaterial,
    PackagingRecord,
    ProductionBatch,
    Product,
)
from .services import available_stock


class BootstrapFormMixin:
    """Give every field a Bootstrap class and make date fields use a date picker."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            widget = field.widget
            if isinstance(widget, forms.CheckboxInput):
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select')
            else:
                widget.attrs.setdefault('class', 'form-control')
            if isinstance(field, forms.DateField):
                widget.input_type = 'date'


class ProductForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            'name', 'sku', 'description', 'size',
            'selling_price', 'reorder_level', 'is_active',
        ]
        widgets = {'description': forms.Textarea(attrs={'rows': 3})}

    def clean_selling_price(self):
        price = self.cleaned_data['selling_price']
        if price < 0:
            raise forms.ValidationError('Selling price cannot be negative.')
        return price


class ProductionBatchForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = ProductionBatch
        fields = [
            'product', 'production_date', 'expiration_date',
            'quantity_produced', 'status', 'notes',
        ]
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['product'].queryset = Product.objects.filter(is_active=True)

    def clean(self):
        cleaned = super().clean()
        produced = cleaned.get('production_date')
        expires = cleaned.get('expiration_date')
        if produced and expires and expires <= produced:
            raise forms.ValidationError(
                'The expiration date must come after the production date.'
            )
        if produced and produced > timezone.localdate():
            raise forms.ValidationError('The production date cannot be in the future.')
        return cleaned

    def save(self, commit=True):
        batch = super().save(commit=False)
        # A brand new batch starts with all of its units waiting to be packaged.
        if batch.pk is None:
            batch.quantity_available = batch.quantity_produced
        if commit:
            batch.save()
        return batch


class PackagingRecordForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = PackagingRecord
        fields = [
            'batch', 'packaging_date', 'quantity_received', 'quantity_packaged',
            'damaged_quantity', 'packaging_staff', 'status', 'remarks',
        ]
        widgets = {'remarks': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['batch'].queryset = ProductionBatch.objects.exclude(
            status=ProductionBatch.STATUS_COMPLETED
        )
        self.fields['packaging_staff'].queryset = User.objects.filter(is_active=True)

    def clean(self):
        cleaned = super().clean()
        received = cleaned.get('quantity_received') or 0
        packaged = cleaned.get('quantity_packaged') or 0
        damaged = cleaned.get('damaged_quantity') or 0
        batch = cleaned.get('batch')

        if packaged + damaged > received:
            raise forms.ValidationError(
                f'Packaged ({packaged}) plus damaged ({damaged}) cannot be more than '
                f'the quantity received ({received}).'
            )
        if batch and received > batch.quantity_available:
            raise forms.ValidationError(
                f'Batch {batch.batch_number} only has {batch.quantity_available} '
                f'unpackaged units available.'
            )
        return cleaned


class PackagingMaterialForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = PackagingMaterial
        fields = ['name', 'quantity_available', 'reorder_level', 'unit', 'is_active']


class InventoryAdjustmentForm(BootstrapFormMixin, forms.Form):
    """Manual stock correction for a single inventory row."""

    new_quantity = forms.IntegerField(min_value=0, label='Corrected quantity')
    reason = forms.CharField(max_length=150, required=False, label='Reason for adjustment')


class CustomerForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            'business_name', 'contact_person', 'phone_number', 'email',
            'address', 'customer_type', 'is_active',
        ]
        widgets = {'address': forms.Textarea(attrs={'rows': 2})}


class OrderForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = Order
        fields = [
            'customer', 'order_date', 'product', 'quantity',
            'unit_price', 'status', 'notes',
        ]
        widgets = {'notes': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.filter(is_active=True)
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
        self.fields['unit_price'].help_text = 'Leave as the suggested price or change it.'

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get('product')
        quantity = cleaned.get('quantity')
        status = cleaned.get('status')

        # Only check stock when the order is being moved towards distribution.
        checked_statuses = [Order.STATUS_PROCESSING, Order.STATUS_READY]
        if product and quantity and status in checked_statuses:
            on_hand = available_stock(product)
            if on_hand < quantity:
                raise forms.ValidationError(
                    f'Only {on_hand} non-expired units of {product.name} are in stock, '
                    f'but this order needs {quantity}. Package more stock first, or '
                    f'keep the order as Pending.'
                )
        return cleaned


class DistributionForm(BootstrapFormMixin, forms.Form):
    """Details captured when an order is shipped."""

    distribution_date = forms.DateField(initial=timezone.localdate)
    delivery_method = forms.ChoiceField(choices=Distribution.METHOD_CHOICES)
    tracking_number = forms.CharField(max_length=50, required=False)
    delivery_status = forms.ChoiceField(
        choices=Distribution.STATUS_CHOICES, initial=Distribution.STATUS_PREPARING
    )
    remarks = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 2}), required=False
    )

    def clean_distribution_date(self):
        date = self.cleaned_data['distribution_date']
        if date > timezone.localdate():
            raise forms.ValidationError('The distribution date cannot be in the future.')
        return date


class DistributionUpdateForm(BootstrapFormMixin, forms.ModelForm):
    """Used to move a shipment along: Preparing -> In Transit -> etc."""

    class Meta:
        model = Distribution
        fields = ['delivery_method', 'tracking_number', 'delivery_status', 'remarks']
        widgets = {'remarks': forms.Textarea(attrs={'rows': 2})}


class DeliveryConfirmationForm(BootstrapFormMixin, forms.ModelForm):
    class Meta:
        model = DeliveryConfirmation
        fields = ['delivery_date', 'receiver_name', 'delivered_quantity', 'remarks']
        widgets = {'remarks': forms.Textarea(attrs={'rows': 2})}

    def __init__(self, *args, distribution=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.distribution = distribution
        if distribution and not self.is_bound:
            self.fields['delivered_quantity'].initial = distribution.quantity_distributed

    def clean_delivery_date(self):
        date = self.cleaned_data['delivery_date']
        if date > timezone.localdate():
            raise forms.ValidationError('The delivery date cannot be in the future.')
        if self.distribution and date < self.distribution.distribution_date:
            raise forms.ValidationError(
                'The delivery date cannot be before the distribution date.'
            )
        return date

    def clean_delivered_quantity(self):
        quantity = self.cleaned_data['delivered_quantity']
        if self.distribution and quantity > self.distribution.quantity_distributed:
            raise forms.ValidationError(
                f'Only {self.distribution.quantity_distributed} units were distributed.'
            )
        return quantity


class UserForm(BootstrapFormMixin, UserCreationForm):
    """Create a system user and put them in the Administrator or Staff group."""

    ROLE_CHOICES = [('Administrator', 'Administrator'), ('Staff', 'Staff')]
    role = forms.ChoiceField(choices=ROLE_CHOICES, initial='Staff')

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
