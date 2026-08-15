"""All URLs for the Guavoco system, grouped by module."""

from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    accounts,
    customers,
    dashboard,
    distribution,
    inventory,
    orders,
    packaging,
    production,
    products,
    reports,
)

urlpatterns = [
    # Authentication
    path('login/', auth_views.LoginView.as_view(
        template_name='registration/login.html', redirect_authenticated_user=True
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # Dashboard
    path('', dashboard.dashboard, name='dashboard'),
    path('activity-log/', dashboard.activity_log, name='activity_log'),

    # Products
    path('products/', products.product_list, name='product_list'),
    path('products/add/', products.product_create, name='product_create'),
    path('products/<int:pk>/', products.product_detail, name='product_detail'),
    path('products/<int:pk>/edit/', products.product_update, name='product_update'),
    path('products/<int:pk>/toggle/', products.product_toggle, name='product_toggle'),

    # Packaging materials
    path('materials/', products.material_list, name='material_list'),
    path('materials/add/', products.material_create, name='material_create'),
    path('materials/<int:pk>/edit/', products.material_update, name='material_update'),
    path('materials/<int:pk>/toggle/', products.material_toggle, name='material_toggle'),

    # Production batches
    path('batches/', production.batch_list, name='batch_list'),
    path('batches/add/', production.batch_create, name='batch_create'),
    path('batches/<int:pk>/', production.batch_detail, name='batch_detail'),
    path('batches/<int:pk>/edit/', production.batch_update, name='batch_update'),

    # Packaging records
    path('packaging/', packaging.packaging_list, name='packaging_list'),
    path('packaging/add/', packaging.packaging_create, name='packaging_create'),
    path('packaging/<int:pk>/edit/', packaging.packaging_update, name='packaging_update'),
    path('packaging/<int:pk>/complete/', packaging.packaging_complete,
         name='packaging_complete'),

    # Inventory
    path('inventory/', inventory.inventory_list, name='inventory_list'),
    path('inventory/<int:pk>/adjust/', inventory.inventory_adjust, name='inventory_adjust'),

    # Customers
    path('customers/', customers.customer_list, name='customer_list'),
    path('customers/add/', customers.customer_create, name='customer_create'),
    path('customers/<int:pk>/', customers.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', customers.customer_update, name='customer_update'),
    path('customers/<int:pk>/toggle/', customers.customer_toggle, name='customer_toggle'),

    # Orders
    path('orders/', orders.order_list, name='order_list'),
    path('orders/add/', orders.order_create, name='order_create'),
    path('orders/<int:pk>/', orders.order_detail, name='order_detail'),
    path('orders/<int:pk>/edit/', orders.order_update, name='order_update'),
    path('orders/<int:pk>/cancel/', orders.order_cancel, name='order_cancel'),
    path('orders/price/<int:product_id>/', orders.product_price, name='product_price'),

    # Distribution and delivery
    path('distribution/', distribution.distribution_list, name='distribution_list'),
    path('distribution/dispatch/<int:order_id>/', distribution.distribute_order_view,
         name='distribute_order'),
    path('distribution/<int:pk>/', distribution.distribution_detail,
         name='distribution_detail'),
    path('distribution/<int:pk>/update/', distribution.distribution_update,
         name='distribution_update'),
    path('distribution/<int:pk>/confirm/', distribution.delivery_confirm,
         name='delivery_confirm'),

    # Reports
    path('reports/', reports.report_index, name='report_index'),
    path('reports/packaging/', reports.packaging_report, name='packaging_report'),
    path('reports/inventory/', reports.inventory_report, name='inventory_report'),
    path('reports/orders/', reports.orders_report, name='orders_report'),
    path('reports/distribution/', reports.distribution_report, name='distribution_report'),
    path('reports/traceability/', reports.batch_traceability, name='batch_traceability'),

    # Users (administrators only)
    path('users/', accounts.user_list, name='user_list'),
    path('users/add/', accounts.user_create, name='user_create'),
    path('users/<int:pk>/toggle/', accounts.user_toggle, name='user_toggle'),
]
