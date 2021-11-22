from django import template

from audit.models import AuditTicketManual, AUDIT_TICKET_STATUS_CHOICES

register = template.Library()

@register.simple_tag
def get_open_ticket_count():
    return AuditTicketManual.objects.filter(status=AUDIT_TICKET_STATUS_CHOICES.OPEN).count()

@register.simple_tag
def get_closed_ticket_count():
    return AuditTicketManual.objects.filter(status=AUDIT_TICKET_STATUS_CHOICES.CLOSED).count()
