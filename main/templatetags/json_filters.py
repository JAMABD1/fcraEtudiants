import json
from django import template
from django.core.serializers.json import DjangoJSONEncoder

register = template.Library()

@register.filter
def to_json(value):
    """
    Convert a Python object to JSON string
    Usage: {{ object|to_json }}
    """
    try:
        return json.dumps(value, cls=DjangoJSONEncoder, ensure_ascii=False)
    except (TypeError, ValueError):
        return '""'

@register.filter
def to_json_safe(value):
    """
    Convert a Python object to JSON string and escape for HTML
    Usage: {{ object|to_json_safe }}
    """
    try:
        json_str = json.dumps(value, cls=DjangoJSONEncoder, ensure_ascii=False)
        # Escape single quotes and double quotes for HTML attribute safety
        return json_str.replace("'", "&#39;").replace('"', "&quot;")
    except (TypeError, ValueError):
        return '""' 