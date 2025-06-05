from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.db.models import Count, Avg, Q, F, ExpressionWrapper, DurationField
from django.utils import timezone
from datetime import timedelta
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
from openpyxl import Workbook
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

from .models import Report, ReportData
from support_system.models import Ticket, User, Category, SupportRating

@login_required
def reports_dashboard(request):
    total_tickets = Ticket.objects.count()
    open_tickets = Ticket.objects.filter(status='open').count()
    inprogress_tickets = Ticket.objects.filter(status='in_progress').count() + Ticket.objects.filter(status='in-progress').count()
    closed_tickets = Ticket.objects.filter(status='closed').count()
    users_count = User.objects.filter(is_support=False, is_admin=False).count()
    support_count = User.objects.filter(is_support=True).count()
    categories_count = Category.objects.count()
    # --- Аналитика по оценкам специалистов ---
    avg_rating = SupportRating.objects.aggregate(avg=Avg('score'))['avg']
    ratings_count = SupportRating.objects.count()
    top_specialists = User.objects.filter(
        specialist_ratings__isnull=False
    ).annotate(
        avg_score=Avg('specialist_ratings__score'),
        ratings_count=Count('specialist_ratings')
    ).order_by('-avg_score')[:5]
    specialists_rating = User.objects.filter(is_support=True).annotate(
        avg_score=Avg('specialist_ratings__score'),
        tickets_count=Count('assigned_tickets', filter=Q(assigned_tickets__status='closed'))
    ).order_by('-avg_score', '-tickets_count')[:10]
    return render(request, 'report_system/dashboard.html', {
        'total_tickets': total_tickets,
        'open_tickets': open_tickets,
        'inprogress_tickets': inprogress_tickets,
        'closed_tickets': closed_tickets,
        'users_count': users_count,
        'support_count': support_count,
        'categories_count': categories_count,
        'avg_rating': avg_rating,
        'ratings_count': ratings_count,
        'top_specialists': top_specialists,
        'specialists_rating': specialists_rating,
    })

@login_required
def generate_tickets_report(request):
    """Генерация отчета по заявкам"""
    # Только для админа и support
    if not (request.user.is_superuser or getattr(request.user, 'is_support', False)):
        return JsonResponse({'error': 'Доступ запрещён'}, status=403)

    # Получаем параметры из запроса
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    category_id = request.GET.get('category_id')
    
    # Базовый запрос
    if request.user.is_superuser:
        tickets = Ticket.objects.all()
    else:
        tickets = Ticket.objects.filter(support_user=request.user)
    
    # Применяем фильтры
    if start_date:
        tickets = tickets.filter(created_at__gte=start_date)
    if end_date:
        tickets = tickets.filter(created_at__lte=end_date)
    if category_id:
        tickets = tickets.filter(category_id=category_id)
    
    # Среднее время решения заявки
    avg_time = tickets.filter(status='closed').annotate(
        duration=ExpressionWrapper(
            F('updated_at') - F('created_at'),
            output_field=DurationField()
        )
    ).aggregate(avg_time=Avg('duration'))['avg_time']
    
    # Собираем статистику
    stats = {
        'total_tickets': tickets.count(),
        'by_status': list(tickets.values('status').annotate(count=Count('id'))),
        'by_category': list(tickets.values(name=F('category__name')).annotate(count=Count('id'))),
        'avg_resolution_time': str(avg_time) if avg_time else None,
    }
    
    return JsonResponse(stats)

@login_required
def generate_support_report(request):
    """Генерация отчета по специалистам поддержки"""
    support_users = User.objects.filter(is_support=True)
    
    stats = []
    for user in support_users:
        user_tickets = Ticket.objects.filter(support_user=user)
        avg_time = user_tickets.filter(status='closed').annotate(
            duration=ExpressionWrapper(F('updated_at') - F('created_at'), output_field=DurationField())
        ).aggregate(avg_time=Avg('duration'))['avg_time']
        stats.append({
            'user': user.username,
            'total_tickets': user_tickets.count(),
            'closed_tickets': user_tickets.filter(status='closed').count(),
            'avg_resolution_time': str(avg_time) if avg_time else None,
        })
    
    return JsonResponse({'support_stats': stats})

@login_required
def generate_users_report(request):
    """Генерация отчета по пользователям"""
    users = User.objects.filter(is_support=False, is_admin=False)
    
    stats = []
    for user in users:
        user_tickets = Ticket.objects.filter(user=user)
        stats.append({
            'user': user.username,
            'total_tickets': user_tickets.count(),
            'active_tickets': user_tickets.filter(status__in=['open', 'in-progress']).count(),
            'closed_tickets': user_tickets.filter(status='closed').count(),
        })
    
    return JsonResponse({'user_stats': stats})

@login_required
def export_report(request, report_id):
    """Экспорт отчета в Excel/PDF"""
    report = get_object_or_404(Report, id=report_id)
    format = request.GET.get('format', 'excel')
    
    if format == 'excel':
        return generate_excel_report(report)
    elif format == 'pdf':
        return generate_pdf_report(report)
    
    return JsonResponse({'error': 'Неподдерживаемый формат'})

def generate_excel_report(report):
    """Генерация Excel-отчета"""
    wb = Workbook()
    ws = wb.active
    ws.title = report.name
    
    # Заполняем данные в зависимости от типа отчета
    if report.report_type == 'tickets':
        ws['A1'] = 'Статистика по заявкам'
        # Добавляем данные...
    
    # Сохраняем в буфер
    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    
    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename="{report.name}.xlsx"'
    return response

def generate_pdf_report(report):
    """Генерация PDF-отчета"""
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    # Заполняем данные в зависимости от типа отчета
    p.drawString(100, 750, f"Отчет: {report.name}")
    # Добавляем данные...
    
    p.showPage()
    p.save()
    buffer.seek(0)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{report.name}.pdf"'
    response.write(buffer.getvalue())
    return response

@login_required
def statistics_dashboard(request):
    total_tickets = Ticket.objects.count()
    open_tickets = Ticket.objects.filter(status='open').count()
    inprogress_tickets = Ticket.objects.filter(status='in_progress').count() + Ticket.objects.filter(status='in-progress').count()
    closed_tickets = Ticket.objects.filter(status='closed').count()
    users_count = User.objects.filter(is_support=False, is_admin=False).count()
    support_count = User.objects.filter(is_support=True).count()
    categories_count = Category.objects.count()
    return render(request, 'report_system/statistics.html', {
        'total_tickets': total_tickets,
        'open_tickets': open_tickets,
        'inprogress_tickets': inprogress_tickets,
        'closed_tickets': closed_tickets,
        'users_count': users_count,
        'support_count': support_count,
        'categories_count': categories_count,
    })
