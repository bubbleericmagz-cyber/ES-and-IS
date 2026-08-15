"""Fill the database with realistic demo data:

    python manage.py seed_demo_data

Running it again wipes the previous demo rows first, so it is safe to repeat
before a presentation.
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import (
    ActivityLog,
    Customer,
    DeliveryConfirmation,
    Distribution,
    DistributionItem,
    Inventory,
    Order,
    PackagingMaterial,
    PackagingRecord,
    Product,
    ProductionBatch,
)
from core.permissions import ADMIN_GROUP, STAFF_GROUP, ensure_groups_exist
from core.services import complete_packaging, confirm_delivery, distribute_order

# A fixed seed means the demo data looks the same every time it is generated.
random.seed(2024)


class Command(BaseCommand):
    help = 'Create demo products, batches, packaging, orders and distributions.'

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Clearing previous demo data ...')
        DeliveryConfirmation.objects.all().delete()
        DistributionItem.objects.all().delete()
        Distribution.objects.all().delete()
        Order.objects.all().delete()
        Inventory.objects.all().delete()
        PackagingRecord.objects.all().delete()
        ProductionBatch.objects.all().delete()
        PackagingMaterial.objects.all().delete()
        Customer.objects.all().delete()
        Product.objects.all().delete()
        ActivityLog.objects.all().delete()

        admin_user, staff_user = self.create_users()
        products = self.create_products()
        self.create_materials()
        batches = self.create_batches(products)
        self.create_packaging(batches, staff_user)
        customers = self.create_customers()
        self.create_orders_and_distributions(products, customers, admin_user, staff_user)

        self.stdout.write(self.style.SUCCESS(
            '\nDemo data is ready.\n'
            '  Administrator: admin / admin123\n'
            '  Staff:         staff / staff123\n'
            '\nStart the server with: python manage.py runserver'
        ))

    # -- users --------------------------------------------------------------

    def create_users(self):
        ensure_groups_exist()
        self.stdout.write('Creating users ...')

        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={'first_name': 'Ana', 'last_name': 'Reyes',
                      'email': 'admin@guavoco.example', 'is_staff': True,
                      'is_superuser': True},
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
        admin_user.groups.add(Group.objects.get(name=ADMIN_GROUP))

        staff_user, created = User.objects.get_or_create(
            username='staff',
            defaults={'first_name': 'Ben', 'last_name': 'Cruz',
                      'email': 'staff@guavoco.example'},
        )
        if created:
            staff_user.set_password('staff123')
            staff_user.save()
        staff_user.groups.add(Group.objects.get(name=STAFF_GROUP))

        return admin_user, staff_user

    # -- master data --------------------------------------------------------

    def create_products(self):
        self.stdout.write('Creating products ...')
        main = Product.objects.create(
            name='Guavoco',
            sku='GVC-TP-001',
            description='Guava and coconut toothpaste. The flagship Guavoco product.',
            size='100g tube',
            selling_price=Decimal('85.00'),
            reorder_level=500,
        )
        mini = Product.objects.create(
            name='Guavoco Mini',
            sku='GVC-TP-002',
            description='Travel size guava and coconut toothpaste.',
            size='50g tube',
            selling_price=Decimal('49.00'),
            reorder_level=300,
        )
        return [main, mini]

    def create_materials(self):
        self.stdout.write('Creating packaging materials ...')
        materials = [
            ('Toothpaste Tubes', 8500, 2000, 'pieces'),
            ('Tube Caps', 9000, 2000, 'pieces'),
            ('Product Boxes', 1500, 2000, 'pieces'),      # low stock on purpose
            ('Product Labels', 12000, 3000, 'pieces'),
            ('Shipping Cartons', 180, 250, 'cartons'),    # low stock on purpose
        ]
        for name, quantity, reorder, unit in materials:
            PackagingMaterial.objects.create(
                name=name, quantity_available=quantity,
                reorder_level=reorder, unit=unit,
            )

    def create_batches(self, products):
        self.stdout.write('Creating production batches ...')
        today = timezone.localdate()
        main, mini = products

        # (product, days ago produced, months until expiry, quantity)
        plans = [
            (main, 300, -1, 3000),   # already expired
            (main, 120, 1, 4000),    # expires within 30 days
            (main, 60, 2, 5000),     # expires within 60 days
            (main, 20, 14, 6000),    # safe
            (mini, 12, 16, 3500),    # safe
            (main, 4, 18, 4500),     # safe, still waiting to be packaged
        ]

        batches = []
        for product, produced_days_ago, expiry_months, quantity in plans:
            production_date = today - timedelta(days=produced_days_ago)
            expiration_date = today + timedelta(days=int(expiry_months * 30))
            batches.append(ProductionBatch.objects.create(
                product=product,
                production_date=production_date,
                expiration_date=expiration_date,
                quantity_produced=quantity,
                quantity_available=quantity,
                status=ProductionBatch.STATUS_READY,
                notes=f'Demo batch of {product.name}.',
            ))
        return batches

    # -- packaging ----------------------------------------------------------

    def create_packaging(self, batches, staff_user):
        self.stdout.write('Recording packaging ...')
        today = timezone.localdate()

        # Every batch except the last one gets packaged, so one batch is left
        # waiting - that is the batch used to demonstrate the workflow live.
        for index, batch in enumerate(batches[:-1]):
            # Package the batch over two sessions so the chart has several bars.
            first_amount = int(batch.quantity_produced * 0.6)
            second_amount = batch.quantity_produced - first_amount

            for session, received in enumerate([first_amount, second_amount]):
                damaged = int(received * random.uniform(0.01, 0.05))
                packaged = received - damaged
                packaging_date = min(
                    today,
                    batch.production_date + timedelta(days=2 + session * 3),
                )
                # Keep recent batches inside the 14 day chart window.
                if index >= 2:
                    packaging_date = today - timedelta(days=(12 - index * 3) - session * 2)
                    packaging_date = max(packaging_date, batch.production_date)
                    packaging_date = min(packaging_date, today)

                record = PackagingRecord.objects.create(
                    batch=batch,
                    packaging_date=packaging_date,
                    quantity_received=received,
                    quantity_packaged=packaged,
                    damaged_quantity=damaged,
                    packaging_staff=staff_user,
                    status=PackagingRecord.STATUS_PENDING,
                    remarks='Demo packaging session.',
                )
                complete_packaging(record, staff_user)

    def create_customers(self):
        self.stdout.write('Creating customers and distributors ...')
        rows = [
            ('Metro Fresh Distribution', 'Liza Santos', '0917-555-0101',
             'liza@metrofresh.example', '12 Mabini St, Quezon City', 'Distributor'),
            ('Sunrise Pharmacy', 'Mark Villanueva', '0918-555-0102',
             'mark@sunrisepharma.example', '88 Rizal Ave, Manila', 'Pharmacy'),
            ('Bayan Grocery Mart', 'Cecil Ramos', '0919-555-0103',
             'cecil@bayangrocery.example', '5 Bonifacio Rd, Cebu City', 'Grocery Store'),
            ('Northside Retail Hub', 'Paolo Diaz', '0920-555-0104',
             'paolo@northside.example', '31 Aurora Blvd, Baguio', 'Retailer'),
            ('Island Care Pharmacy', 'Grace Lim', '0921-555-0105',
             'grace@islandcare.example', '77 Osmena St, Iloilo', 'Pharmacy'),
            ('Ella Mendoza', 'Ella Mendoza', '0922-555-0106',
             'ella@example.com', '9 Sampaguita St, Davao', 'Direct Customer'),
        ]
        return [
            Customer.objects.create(
                business_name=name, contact_person=contact, phone_number=phone,
                email=email, address=address, customer_type=ctype,
            )
            for name, contact, phone, email, address, ctype in rows
        ]

    # -- orders, distributions, deliveries ----------------------------------

    def create_orders_and_distributions(self, products, customers, admin_user, staff_user):
        self.stdout.write('Creating orders and distributions ...')
        today = timezone.localdate()
        main = products[0]

        # (days ago, customer index, product, quantity, how far the order got)
        plans = [
            (13, 0, main, 400, 'delivered'),
            (12, 1, main, 150, 'delivered'),
            (11, 2, main, 250, 'delivered'),
            (10, 3, main, 300, 'delivered'),
            (8, 4, main, 180, 'in_transit'),
            (7, 0, main, 500, 'in_transit'),
            (5, 5, products[1], 120, 'distributed'),
            (4, 2, main, 220, 'distributed'),
            (3, 1, main, 160, 'ready'),
            (2, 3, main, 340, 'processing'),
            (1, 4, main, 200, 'pending'),
            (0, 5, main, 90, 'pending'),
            (6, 0, main, 700, 'cancelled'),
        ]

        for days_ago, customer_index, product, quantity, stage in plans:
            order_date = today - timedelta(days=days_ago)
            order = Order.objects.create(
                customer=customers[customer_index],
                order_date=order_date,
                product=product,
                quantity=quantity,
                unit_price=product.selling_price,
                status=Order.STATUS_PENDING,
                notes='Demo order.',
            )
            ActivityLog.objects.create(
                user=admin_user, action='Order Created',
                description=f'{order.order_number}: {quantity} x {product.name} for '
                            f'{order.customer.business_name}.',
                timestamp=timezone.make_aware(
                    timezone.datetime.combine(order_date, timezone.datetime.min.time())
                ) + timedelta(hours=9),
            )

            if stage == 'pending':
                continue
            if stage == 'cancelled':
                order.status = Order.STATUS_CANCELLED
                order.save()
                continue
            if stage == 'processing':
                order.status = Order.STATUS_PROCESSING
                order.save()
                continue
            if stage == 'ready':
                order.status = Order.STATUS_READY
                order.save()
                continue

            # The rest are shipped, which deducts real stock from inventory.
            shipping_date = min(today, order_date + timedelta(days=1))
            method = random.choice([choice[0] for choice in Distribution.METHOD_CHOICES])
            shipment = distribute_order(order, {
                'distribution_date': shipping_date,
                'delivery_method': method,
                'tracking_number': f'TRK{random.randint(100000, 999999)}',
                'delivery_status': Distribution.STATUS_IN_TRANSIT,
                'remarks': 'Demo shipment.',
            }, staff_user)

            if stage == 'delivered':
                delivery_date = min(today, shipping_date + timedelta(days=2))
                confirm_delivery(shipment, DeliveryConfirmation(
                    delivery_date=delivery_date,
                    receiver_name=order.customer.contact_person,
                    delivered_quantity=order.quantity,
                    remarks='Received in good condition.',
                ), staff_user)
