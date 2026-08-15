# Guavoco Packaging & Distribution Management System

A school-project prototype that tracks **Guavoco** guava-and-coconut toothpaste from
production through packaging, inventory, customer orders, distribution and final
delivery.

Built with Python, Django 5.2, SQLite, Bootstrap 5 and Chart.js.

```
Production Batch -> Packaging -> Finished Inventory -> Order -> Distribution -> Delivered
```

---

## 1. How to run it

Open a terminal in this folder (`guavoco_system`) and run:

```powershell
.venv\Scripts\python.exe manage.py runserver
```

Then open <http://127.0.0.1:8000/> in a browser.

Calling `.venv\Scripts\python.exe` directly means the virtual environment does
**not** need to be activated. Windows PowerShell blocks activation scripts by
default, so this is the reliable way to run the project.

Every other command works the same way, for example:

```powershell
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py seed_demo_data
.venv\Scripts\python.exe manage.py createsuperuser
```

<details>
<summary>Optional: if you would rather type <code>python manage.py ...</code></summary>

Activation fails with *"running scripts is disabled on this system"* until you
allow local scripts for your own user account. Run this once:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

After that, `.venv\Scripts\activate` works and you can use the shorter
`python manage.py runserver`.

</details>

### Demo accounts

| Role | Username | Password | Can do |
|---|---|---|---|
| Administrator | `admin` | `admin123` | Everything, including products, batches, customers and users |
| Staff | `staff` | `staff123` | Dashboard, packaging, orders, distribution, inventory, reports |

The database already contains demo data. To reset it right before a presentation,
run `.venv\Scripts\python.exe manage.py seed_demo_data` again — it clears the old
demo rows first, so it is safe to repeat.

### Setting it up on another computer

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe manage.py migrate
.venv\Scripts\python.exe manage.py seed_demo_data
.venv\Scripts\python.exe manage.py runserver
```

Bootstrap and Chart.js are stored in `static/vendor/`, so the system works with no
internet connection.

---

## 2. Presentation script

This is the complete workflow the prototype demonstrates. Each step can be shown
live in about five minutes.

| # | Step | What to point out |
|---|---|---|
| 1 | Log in as `admin` | Every page requires a login |
| 2 | **Dashboard** | Seven summary cards and four charts, all read from the database |
| 3 | **Products** -> Add Product | SKU `GVC-TP-001` is the main Guavoco toothpaste |
| 4 | **Production Batches** -> Add Batch | The batch number `GVC-BATCH-00xx` is generated automatically |
| 5 | **Packaging** -> Record Packaging | Enter received 1000, packaged 950, damaged 50. Remaining becomes 0 and efficiency shows 95% |
| 6 | Click **Complete** on that record | 950 units appear in **Inventory**; the batch's unpackaged count drops to 0 |
| 7 | **Customers** -> Add Customer | Add a distributor |
| 8 | **Orders** -> Create Order | Total Amount is calculated as Quantity x Unit Price |
| 9 | Try an order bigger than stock | The system refuses it and says how many units are actually available |
| 10 | **Distribute** the valid order | Stock is deducted, order becomes *Distributed*, a `GVC-DIST-00xx` record is created |
| 11 | **Confirm Delivery** | Order and shipment both become *Delivered* |
| 12 | **Reports** | Filter by date, product and status, then **Export CSV** |
| 13 | **Batch Traceability** | Enter the batch number and show the customer who received it |
| 14 | Back to the **Dashboard** | Every card and chart has updated |

### Rules worth demonstrating

- Packaging more units than the batch holds is rejected.
- Packaged + damaged can never be more than the quantity received.
- An order cannot be distributed if there is not enough stock.
- **Expired batches are skipped when shipping**, so expired product can never leave.
- Stock is taken **first-expiry-first-out**, so the oldest usable batch ships first.
- Inventory can never go below zero.
- A Staff login cannot see the Users page or edit products.

---

## 3. Project structure

```
guavoco_system/
├── manage.py
├── requirements.txt
├── db.sqlite3
│
├── guavoco_system/          Django project settings and root URLs
│
├── core/                    The whole application lives in one app
│   ├── models.py            All 12 database models
│   ├── forms.py             Every data entry form, with validation
│   ├── services.py          The business rules that move stock around
│   ├── permissions.py       Administrator / Staff roles
│   ├── urls.py
│   ├── admin.py
│   ├── views/               One file per part of the system
│   │   ├── dashboard.py     Summary cards, chart data, activity log
│   │   ├── products.py      Products and packaging materials
│   │   ├── production.py    Production batches
│   │   ├── packaging.py     Packaging records
│   │   ├── inventory.py     Finished product inventory
│   │   ├── customers.py
│   │   ├── orders.py
│   │   ├── distribution.py  Shipping and delivery confirmation
│   │   ├── reports.py       Reports, CSV export, batch traceability
│   │   └── accounts.py      User management
│   ├── context_processors.py            Role, page subtitle, alert counts
│   ├── templatetags/guavoco_extras.py    Status -> badge tone
│   └── management/commands/seed_demo_data.py
│
├── templates/
│   ├── base.html            Sidebar, top bar, notifications, profile menu
│   ├── components/          Reusable pieces (see below)
│   └── <module>/            One folder per part of the system
└── static/
    ├── css/guavoco-theme.css  The Guavoco theme, loaded after Bootstrap
    ├── js/dashboard.js        The four Chart.js charts
    └── vendor/                Bootstrap 5 and Chart.js, stored locally
```

### Reusable template components

| Component | What it renders |
|---|---|
| `components/stat_card.html` | A KPI card: white surface, tinted icon, dark number, muted label |
| `components/status_badge.html` | A soft status pill, coloured by the `\|badge` filter |
| `components/empty_state.html` | The "nothing here yet" message with an icon and optional button |
| `components/table_card.html` | The heading strip above a table |
| `components/icons.html` | The inline SVG icon sprite, used as `<use href="#i-box">` |

---

## 4. Visual design

The interface follows the Guavoco toothpaste packaging: natural greens, coconut
cream, white and small guava coral accents.

```
Coconut cream page background  #F3EFE7
        v
White cards, tables and forms  #FFFFFF
        v
Deep green sidebar and primary buttons  #3F5A1A
        v
Fresh leaf green secondary accents  #6E8B2C
        v
Soft sage  #A8B39A   and small guava coral highlights  #F27F6A
```

All of it lives in one file, `static/css/guavoco-theme.css`, which is loaded
**after** Bootstrap so it overrides the defaults. Colours are defined once as CSS
variables at the top of that file, so the whole system can be recoloured by
editing those few lines.

A few notes on the choices:

- **Coral is an accent, never a surface.** It appears on the notification dot,
  the "damaged" and "low stock" icons, the cancelled-orders bar in the chart and
  the small rule on the login page - nowhere else.
- **Status badges are soft, not saturated.** `core/templatetags/guavoco_extras.py`
  maps each status word to one of eight tones (success, progress, primary,
  pending, lowstock, danger, transit, neutral).
- **Charts group the order statuses by meaning** - leaf green for the stages in
  progress, deep green for Delivered, coral for Cancelled - rather than giving
  each of the six statuses its own hue. Six muted botanical colours would not be
  reliably distinguishable, especially for colourblind readers; every bar is also
  labelled on its own axis, so colour is never the only cue.
- **Icons are inline SVG**, so the system still needs no internet connection.

---

## 5. The database models

| Model | What it stores |
|---|---|
| `Product` | Guavoco toothpaste and its variants |
| `ProductionBatch` | One production run: `GVC-BATCH-0001` |
| `PackagingRecord` | How many units of a batch were packaged or damaged: `GVC-PKG-0001` |
| `PackagingMaterial` | Tubes, caps, boxes, labels, cartons: `GVC-MAT-0001` |
| `Inventory` | Finished stock, one row per product and batch |
| `Customer` | Distributors, retailers, pharmacies and direct buyers: `GVC-CUS-0001` |
| `Order` | A customer order: `GVC-ORD-0001` |
| `Distribution` | A shipment fulfilling an order: `GVC-DIST-0001` |
| `DistributionItem` | Which batch each shipped unit came from |
| `DeliveryConfirmation` | Who received a delivery, and when |
| `ActivityLog` | A record of the important actions users take |
| `User` | Django's built-in user, in the Administrator or Staff group |

`DistributionItem` is the small extra table that makes batch traceability work. One
order can be filled from more than one batch, so a row is saved for each batch used.
That is how the traceability page can list exactly which customers received products
from a given batch.

### Where the numbers come from

Nothing on the dashboard is hardcoded. A few useful details:

- `Product.current_stock` is **calculated** by summing the inventory rows, so it can
  never disagree with the inventory table.
- `PackagingRecord.remaining_quantity` is worked out in `save()` as
  `received - packaged - damaged`, and is never allowed below zero.
- `Order.total_amount` is worked out in `save()` as `quantity x unit_price`.
- `PackagingRecord.efficiency` is `packaged / received x 100`.
- Inventory status (Available / Low Stock / Out of Stock / Expired) and expiry badges
  (Safe / Expiring in 30 Days / Expiring in 60 Days / Expired) are calculated
  from the expiration date each time a page is loaded.

All stock movements live in `core/services.py`:

| Function | What it does |
|---|---|
| `complete_packaging` | Takes units out of a batch and adds them to inventory |
| `available_stock` | Sellable units of a product, excluding expired batches |
| `distribute_order` | Checks stock, allocates first-expiry-first-out, deducts inventory, creates the shipment |
| `confirm_delivery` | Marks the shipment and the order as delivered |
| `adjust_inventory` | A manual stock correction, floored at zero |

---

## 6. Features

- **Dashboard** with seven live summary cards and four Chart.js charts
  (packaging activity, distribution activity, inventory per product, orders per status)
- **Products** with SKU, price, reorder level and low-stock warnings
- **Production batches** with automatic batch numbers and expiry monitoring
- **Packaging records** with automatic remaining-quantity and packaging efficiency
- **Packaging materials** inventory with Normal Stock / Low Stock badges
- **Finished product inventory** with manual adjustment and expiry badges
- **Customers and distributors** across five customer types
- **Orders** with automatic totals and a stock check before preparation
- **Distribution** with first-expiry-first-out stock allocation and delivery statuses
- **Delivery confirmation** that closes the order
- **Four reports**, all filterable by date range, product and status, all exportable to CSV
- **Batch traceability** from production to the customers who received the product
- **Activity log** of every important action
- **User management** with Administrator and Staff roles
- Search and filters on every important table
