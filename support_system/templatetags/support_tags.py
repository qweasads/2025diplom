from django import template

register = template.Library()

@register.filter
def filter_status(tickets, status):
    return [ticket for ticket in tickets if ticket.status == status]

@register.filter
def status_badge(status):
    """Возвращает класс бейджа для статуса заявки"""
    status_classes = {
        'open': 'warning',
        'in_progress': 'primary',
        'closed': 'success'
    }
    return status_classes.get(status, 'secondary') 