"""Small template helpers, mainly for turning a status word into a badge tone."""

from django import template

register = template.Library()

# Every status used anywhere in the system, mapped to a Guavoco badge tone.
# The tones themselves are defined in static/css/guavoco-theme.css as
# .gv-badge--<tone>, using soft botanical colours instead of Bootstrap's
# saturated defaults.
BADGE_TONES = {
    # Products and inventory
    'Available': 'success',
    'Normal Stock': 'success',
    'Low Stock': 'lowstock',
    'Out of Stock': 'danger',
    'Expired': 'danger',
    'Active': 'success',
    'Inactive': 'neutral',
    # Expiry
    'Safe': 'success',
    'Expiring in 30 Days': 'danger',
    'Expiring in 60 Days': 'lowstock',
    # Batches
    'Produced': 'neutral',
    'Ready for Packaging': 'progress',
    'Packaged': 'primary',
    'Completed': 'success',
    # Packaging records
    'Pending': 'pending',
    'In Progress': 'progress',
    # Orders
    'Processing': 'progress',
    'Ready for Distribution': 'primary',
    'Distributed': 'transit',
    'Delivered': 'success',
    'Cancelled': 'danger',
    # Distribution
    'Preparing': 'neutral',
    'For Delivery': 'transit',
    'In Transit': 'transit',
    # Roles
    'Administrator': 'primary',
    'Staff': 'progress',
}


@register.filter
def badge(status):
    """Usage: <span class="gv-badge gv-badge--{{ order.status|badge }}">

    Most templates use the components/status_badge.html partial instead of
    calling this directly.
    """
    return BADGE_TONES.get(str(status), 'neutral')


@register.simple_tag
def query_string(request, **overrides):
    """Rebuild the current query string with some values replaced.

    Used by pagination links so the active search and filters are kept.
    """
    params = request.GET.copy()
    for key, value in overrides.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()
