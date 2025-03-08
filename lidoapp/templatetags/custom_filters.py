from datetime import timedelta, datetime
from django import template
from django.utils.timezone import make_aware, is_naive

register = template.Library()

@register.filter
def get_item(list, index):
    try:
        return list[index]
    except IndexError:
        return None

@register.filter
def date_add(value, days):
    from datetime import datetime, timedelta

    try:
        # If `value` is a string, convert it to a datetime object
        if isinstance(value, str):
            value = datetime.strptime(value, "%Y-%m-%d")
        # Add the number of days to the value
        return (value + timedelta(days=int(days))).strftime("%Y-%m-%d")
    except Exception:
        return value  # Return the original value if an error occurs
    
@register.filter
def date_diff(date1, date2):
    from django.utils.timezone import now, make_aware, is_naive

    try:
        # Convert date1 to datetime if it is a string
        if isinstance(date1, str):
            date1 = datetime.strptime(date1, "%Y-%m-%d")
        if isinstance(date2, str):
            date2 = datetime.strptime(date2, "%Y-%m-%d")

        # Ensure both dates are timezone-aware
        if is_naive(date1):
            date1 = make_aware(date1)
        if is_naive(date2):
            date2 = make_aware(date2)

        # Calculate the difference in days
        return (date1 - date2).days
    except Exception as e:
        return 0  # Return 0 if there's an error


@register.filter
def in_list(value, list_str):
    """Check if a value is in a comma-separated string."""
    return value in list_str.split(',')