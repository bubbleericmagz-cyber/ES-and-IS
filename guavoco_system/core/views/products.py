"""Product management and the packaging materials inventory."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import PackagingMaterialForm, ProductForm
from ..models import ActivityLog, PackagingMaterial, Product
from ..permissions import administrator_required


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------

@login_required
def product_list(request):
    products = Product.objects.all()

    search = request.GET.get('q', '').strip()
    if search:
        products = products.filter(Q(name__icontains=search) | Q(sku__icontains=search))

    status = request.GET.get('status', '')
    if status == 'active':
        products = products.filter(is_active=True)
    elif status == 'inactive':
        products = products.filter(is_active=False)

    context = {
        'page_title': 'Products',
        'products': products,
        'search': search,
        'status': status,
    }
    return render(request, 'products/product_list.html', context)


@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    context = {
        'page_title': product.name,
        'product': product,
        'batches': product.batches.all()[:10],
        'inventory_rows': product.inventory_rows.select_related('batch'),
        'recent_orders': product.orders.select_related('customer')[:10],
    }
    return render(request, 'products/product_detail.html', context)


@login_required
@administrator_required
def product_create(request):
    form = ProductForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        product = form.save()
        ActivityLog.record(request.user, 'Product Added',
                           f'{product.name} ({product.sku}) was created.')
        messages.success(request, f'Product "{product.name}" was added.')
        return redirect('product_list')
    return render(request, 'products/product_form.html',
                  {'page_title': 'Add Product', 'form': form})


@login_required
@administrator_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        ActivityLog.record(request.user, 'Product Updated', f'{product.name} was edited.')
        messages.success(request, f'Product "{product.name}" was updated.')
        return redirect('product_list')
    return render(request, 'products/product_form.html',
                  {'page_title': f'Edit {product.name}', 'form': form, 'product': product})


@login_required
@administrator_required
def product_toggle(request, pk):
    """Products are never deleted, only deactivated, so history stays intact."""
    product = get_object_or_404(Product, pk=pk)
    product.is_active = not product.is_active
    product.save()
    state = 'activated' if product.is_active else 'deactivated'
    ActivityLog.record(request.user, 'Product Updated', f'{product.name} was {state}.')
    messages.success(request, f'Product "{product.name}" was {state}.')
    return redirect('product_list')


# ---------------------------------------------------------------------------
# Packaging materials
# ---------------------------------------------------------------------------

@login_required
def material_list(request):
    materials = PackagingMaterial.objects.all()

    search = request.GET.get('q', '').strip()
    if search:
        materials = materials.filter(name__icontains=search)

    status = request.GET.get('status', '')
    materials = list(materials)
    if status == 'low':
        materials = [m for m in materials if m.is_low_stock]
    elif status == 'normal':
        materials = [m for m in materials if not m.is_low_stock]

    context = {
        'page_title': 'Packaging Materials',
        'materials': materials,
        'search': search,
        'status': status,
    }
    return render(request, 'products/material_list.html', context)


@login_required
@administrator_required
def material_create(request):
    form = PackagingMaterialForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        material = form.save()
        ActivityLog.record(request.user, 'Material Added', f'{material.name} was created.')
        messages.success(request, f'Material "{material.name}" was added.')
        return redirect('material_list')
    return render(request, 'products/material_form.html',
                  {'page_title': 'Add Packaging Material', 'form': form})


@login_required
@administrator_required
def material_update(request, pk):
    material = get_object_or_404(PackagingMaterial, pk=pk)
    form = PackagingMaterialForm(request.POST or None, instance=material)
    if request.method == 'POST' and form.is_valid():
        form.save()
        ActivityLog.record(request.user, 'Material Updated', f'{material.name} was edited.')
        messages.success(request, f'Material "{material.name}" was updated.')
        return redirect('material_list')
    return render(request, 'products/material_form.html',
                  {'page_title': f'Edit {material.name}', 'form': form})


@login_required
@administrator_required
def material_toggle(request, pk):
    material = get_object_or_404(PackagingMaterial, pk=pk)
    material.is_active = not material.is_active
    material.save()
    state = 'activated' if material.is_active else 'deactivated'
    messages.success(request, f'Material "{material.name}" was {state}.')
    return redirect('material_list')
