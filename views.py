from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

from .models import User, Category, Ticket, TicketMessage, TicketFile, MessageFile, Notification, FAQ, KnowledgeBase
from .forms import (
    LoginForm, RegisterForm, TicketForm, TicketMessageForm, 
    UserForm, SupportUserForm, CategoryForm, FAQForm, KnowledgeBaseForm
)
from .decorators import admin_required, support_required


def index(request):
    """Главная страница"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    categories = Category.objects.all()
    faqs = FAQ.objects.all()[:5]
    
    return render(request, 'index.html', {
        'categories': categories,
        'faqs': faqs,
    })


def login_view(request):
    """Страница входа"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                login(request, user)
                messages.success(request, 'Вы успешно вошли в систему.')
                return redirect('dashboard')
            else:
                messages.error(request, 'Неверное имя пользователя или пароль.')
    else:
        form = LoginForm()
    
    return render(request, 'login.html', {'form': form})


def register_view(request):
    """Страница регистрации"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Вы успешно зарегистрировались.')
            return redirect('dashboard')
    else:
        form = RegisterForm()
    
    return render(request, 'register.html', {'form': form})


@login_required
def logout_view(request):
    """Выход из системы"""
    logout(request)
    messages.success(request, 'Вы успешно вышли из системы.')
    return redirect('login')


@login_required
def dashboard(request):
    """Главная страница после входа"""
    user = request.user
    
    if user.is_admin:
        # Данные для администратора
        total_tickets = Ticket.objects.count()
        open_tickets = Ticket.objects.filter(status='open').count()
        in_progress_tickets = Ticket.objects.filter(status='in-progress').count()
        closed_tickets = Ticket.objects.filter(status='closed').count()
        total_users = User.objects.filter(is_admin=False, is_support=False).count()
        total_support = User.objects.filter(is_support=True).count()
        recent_tickets = Ticket.objects.all()[:10]
        
        return render(request, 'dashboard.html', {
            'total_tickets': total_tickets,
            'open_tickets': open_tickets,
            'in_progress_tickets': in_progress_tickets,
            'closed_tickets': closed_tickets,
            'total_users': total_users,
            'total_support': total_support,
            'recent_tickets': recent_tickets,
        })
    
    elif user.is_support:
        # Данные для специалиста поддержки
        assigned_tickets = Ticket.objects.filter(support_user=user).count()
        open_assigned_tickets = Ticket.objects.filter(support_user=user, status='open').count()
        in_progress_assigned_tickets = Ticket.objects.filter(support_user=user, status='in-progress').count()
        closed_assigned_tickets = Ticket.objects.filter(support_user=user, status='closed').count()
        
        # Получаем заявки по категориям, назначенным специалисту
        user_categories = user.categories.all()
        open_tickets = Ticket.objects.filter(
            Q(support_user=user) | Q(category__in=user_categories, support_user__isnull=True),
            status='open'
        )
        in_progress_tickets = Ticket.objects.filter(support_user=user, status='in-progress')
        closed_tickets = Ticket.objects.filter(support_user=user, status='closed')
        
        return render(request, 'dashboard.html', {
            'assigned_tickets': assigned_tickets,
            'open_assigned_tickets': open_assigned_tickets,
            'in_progress_assigned_tickets': in_progress_assigned_tickets,
            'closed_assigned_tickets': closed_assigned_tickets,
            'open_tickets': open_tickets,
            'in_progress_tickets': in_progress_tickets,
            'closed_tickets': closed_tickets,
        })
    
    else:
        # Данные для обычного пользователя
        user_tickets_count = Ticket.objects.filter(user=user).count()
        user_open_tickets_count = Ticket.objects.filter(user=user, status__in=['open', 'in-progress']).count()
        user_closed_tickets_count = Ticket.objects.filter(user=user, status='closed').count()
        user_recent_tickets = Ticket.objects.filter(user=user).order_by('-created_at')[:5]
        
        return render(request, 'dashboard.html', {
            'user_tickets_count': user_tickets_count,
            'user_open_tickets_count': user_open_tickets_count,
            'user_closed_tickets_count': user_closed_tickets_count,
            'user_recent_tickets': user_recent_tickets,
        })


@login_required
def create_ticket(request):
    """Создание новой заявки"""
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            # Создаем заявку
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.save()
            
            # Обрабатываем прикрепленные файлы
            files = request.FILES.getlist('files')
            for file in files:
                TicketFile.objects.create(
                    ticket=ticket,
                    file=file,
                    filename=file.name
                )
            
            # Создаем уведомления для специалистов поддержки
            support_users = ticket.category.support_users.all()
            for support_user in support_users:
                Notification.objects.create(
                    user=support_user,
                    ticket=ticket,
                    type='ticket_created',
                    text=f'Новая заявка #{ticket.id}: {ticket.title}'
                )
            
            messages.success(request, 'Заявка успешно создана.')
            return redirect('ticket_detail', ticket_id=ticket.id)
    else:
        form = TicketForm()
    
    categories = Category.objects.all()
    
    return render(request, 'create_ticket.html', {
        'form': form,
        'categories': categories,
    })


@login_required
def ticket_detail(request, ticket_id):
    """Просмотр детальной информации о заявке"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Проверяем права доступа
    if not (request.user == ticket.user or request.user.is_admin or 
            (request.user.is_support and (request.user == ticket.support_user or 
                                         ticket.category in request.user.categories.all()))):
        messages.error(request, 'У вас нет доступа к этой заявке.')
        return redirect('dashboard')
    
    # Отмечаем уведомления как прочитанные
    Notification.objects.filter(user=request.user, ticket=ticket, is_read=False).update(is_read=True)
    
    return render(request, 'ticket_detail.html', {
        'ticket': ticket,
    })


@login_required
def reply_ticket(request, ticket_id):
    """Ответ на заявку"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Проверяем права доступа
    if not (request.user == ticket.user or request.user.is_admin or 
            (request.user.is_support and (request.user == ticket.support_user or 
                                         ticket.category in request.user.categories.all()))):
        messages.error(request, 'У вас нет доступа к этой заявке.')
        return redirect('dashboard')
    
    if ticket.status == 'closed':
        messages.error(request, 'Эта заявка закрыта. Вы не можете отправлять новые сообщения.')
        return redirect('ticket_detail', ticket_id=ticket.id)
    
    if request.method == 'POST':
        form = TicketMessageForm(request.POST, request.FILES)
        if form.is_valid():
            # Создаем сообщение
            message = form.save(commit=False)
            message.ticket = ticket
            message.user = request.user
            message.save()
            
            # Обрабатываем прикрепленные файлы
            files = request.FILES.getlist('files')
            for file in files:
                MessageFile.objects.create(
                    message=message,
                    file=file,
                    filename=file.name
                )
            
            # Если специалист поддержки отвечает, обновляем статус заявки
            if request.user.is_support and ticket.status == 'open':
                ticket.status = 'in-progress'
                ticket.save()
            
            # Если специалист не назначен и отвечает специалист поддержки, назначаем его
            if request.user.is_support and not ticket.support_user:
                ticket.support_user = request.user
                ticket.save()
            
            # Создаем уведомления
            if request.user == ticket.user:
                # Если отвечает пользователь, уведомляем специалиста поддержки
                if ticket.support_user:
                    Notification.objects.create(
                        user=ticket.support_user,
                        ticket=ticket,
                        message=message,
                        type='message_created',
                        text=f'Новое сообщение в заявке #{ticket.id}'
                    )
                else:
                    # Уведомляем всех специалистов поддержки, назначенных на этот раздел
                    support_users = ticket.category.support_users.all()
                    for support_user in support_users:
                        Notification.objects.create(
                            user=support_user,
                            ticket=ticket,
                            message=message,
                            type='message_created',
                            text=f'Новое сообщение в заявке #{ticket.id}'
                        )
            else:
                # Если отвечает специалист поддержки, уведомляем пользователя
                Notification.objects.create(
                    user=ticket.user,
                    ticket=ticket,
                    message=message,
                    type='message_created',
                    text=f'Новый ответ на вашу заявку #{ticket.id}'
                )
                
                # Отправляем email-уведомление пользователю
                send_mail(
                    f'Новый ответ на вашу заявку #{ticket.id}',
                    f'Здравствуйте, {ticket.user.get_full_name()}!\n\nВы получили новый ответ на вашу заявку #{ticket.id}: {ticket.title}.\n\nПожалуйста, войдите в систему, чтобы просмотреть ответ.\n\nС уважением,\nСлужба поддержки',
                    settings.DEFAULT_FROM_EMAIL,
                    [ticket.user.email],
                    fail_silently=True,
                )
            
            messages.success(request, 'Сообщение успешно отправлено.')
            return redirect('ticket_detail', ticket_id=ticket.id)
    else:
        form = TicketMessageForm()
    
    return render(request, 'reply_ticket.html', {
        'form': form,
        'ticket': ticket,
    })


@login_required
def user_tickets(request):
    """Список заявок пользователя"""
    tickets = Ticket.objects.filter(user=request.user).order_by('-created_at')
    
    # Фильтрация по статусу
    status = request.GET.get('status')
    if status:
        tickets = tickets.filter(status=status)
    
    # Поиск
    search = request.GET.get('search')
    if search:
        tickets = tickets.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search) | 
            Q(id__icontains=search)
        )
    
    # Пагинация
    paginator = Paginator(tickets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'user_tickets.html', {
        'tickets': page_obj,
    })


@login_required
@support_required
def support_tickets(request):
    """Список заявок для специалиста поддержки"""
    user = request.user
    
    # Получаем заявки, назначенные специалисту или относящиеся к его категориям
    user_categories = user.categories.all()
    tickets = Ticket.objects.filter(
        Q(support_user=user) | Q(category__in=user_categories, support_user__isnull=True)
    ).order_by('-created_at')
    
    # Фильтрация по статусу
    status = request.GET.get('status')
    if status:
        tickets = tickets.filter(status=status)
    
    # Поиск
    search = request.GET.get('search')
    if search:
        tickets = tickets.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search) | 
            Q(id__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    # Пагинация
    paginator = Paginator(tickets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'support_tickets.html', {
        'tickets': page_obj,
    })


@login_required
@admin_required
def admin_tickets(request):
    """Список всех заявок для администратора"""
    tickets = Ticket.objects.all().order_by('-created_at')
    
    # Фильтрация по статусу
    status = request.GET.get('status')
    if status:
        tickets = tickets.filter(status=status)
    
    # Фильтрация по категории
    category_id = request.GET.get('category')
    if category_id:
        tickets = tickets.filter(category_id=category_id)
    
    # Поиск
    search = request.GET.get('search')
    if search:
        tickets = tickets.filter(
            Q(title__icontains=search) | 
            Q(description__icontains=search) | 
            Q(id__icontains=search) |
            Q(user__first_name__icontains=search) |
            Q(user__last_name__icontains=search) |
            Q(user__email__icontains=search)
        )
    
    # Пагинация
    paginator = Paginator(tickets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = Category.objects.all()
    
    return render(request, 'admin/admin_tickets.html', {
        'tickets': page_obj,
        'categories': categories,
    })


@login_required
@require_POST
def update_ticket_status(request, ticket_id):
    """Обновление статуса заявки"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Проверяем права доступа
    if not (request.user.is_admin or 
            (request.user.is_support and (request.user == ticket.support_user or 
                                         ticket.category in request.user.categories.all()))):
        return JsonResponse({'success': False, 'error': 'У вас нет доступа к этой заявке.'})
    
    status = request.POST.get('status')
    if status not in [s[0] for s in Ticket.STATUS_CHOICES]:
        return JsonResponse({'success': False, 'error': 'Неверный статус.'})
    
    ticket.status = status
    ticket.save()
    
    # Создаем уведомление для пользователя
    Notification.objects.create(
        user=ticket.user,
        ticket=ticket,
        type='ticket_updated',
        text=f'Статус вашей заявки #{ticket.id} изменен на "{ticket.get_status_display()}"'
    )
    
    # Отправляем email-уведомление пользователю
    send_mail(
        f'Статус вашей заявки #{ticket.id} изменен',
        f'Здравствуйте, {ticket.user.get_full_name()}!\n\nСтатус вашей заявки #{ticket.id}: {ticket.title} изменен на "{ticket.get_status_display()}".\n\nС уважением,\nСлужба поддержки',
        settings.DEFAULT_FROM_EMAIL,
        [ticket.user.email],
        fail_silently=True,
    )
    
    return JsonResponse({'success': True})


@login_required
@admin_required
def assign_ticket(request, ticket_id):
    """Назначение специалиста поддержки на заявку"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    if request.method == 'POST':
        support_user_id = request.POST.get('support_user')
        support_user = get_object_or_404(User, id=support_user_id, is_support=True)
        
        ticket.support_user = support_user
        ticket.save()
        
        # Создаем уведомление для специалиста поддержки
        Notification.objects.create(
            user=support_user,
            ticket=ticket,
            type='ticket_assigned',
            text=f'Вам назначена заявка #{ticket.id}: {ticket.title}'
        )
        
        messages.success(request, f'Заявка #{ticket.id} успешно назначена специалисту {support_user.get_full_name()}.')
        return redirect('ticket_detail', ticket_id=ticket.id)
    
    support_users = User.objects.filter(is_support=True)
    
    return render(request, 'admin/assign_ticket.html', {
        'ticket': ticket,
        'support_users': support_users,
    })


@login_required
@admin_required
def admin_panel(request):
    """Админ-панель"""
    total_tickets = Ticket.objects.count()
    open_tickets = Ticket.objects.filter(status='open').count()
    in_progress_tickets = Ticket.objects.filter(status='in-progress').count()
    closed_tickets = Ticket.objects.filter(status='closed').count()
    total_users = User.objects.filter(is_admin=False, is_support=False).count()
    total_support = User.objects.filter(is_support=True).count()
    total_categories = Category.objects.count()
    
    # Данные для графиков
    categories = Category.objects.annotate(tickets_count=Count('tickets'))
    
    # Данные для графика динамики заявок
    today = timezone.now().date()
    timeline_dates = []
    timeline_counts = []
    
    for i in range(30, -1, -1):
        date = today - timedelta(days=i)
        count = Ticket.objects.filter(created_at__date=date).count()
        timeline_dates.append(date.strftime('%d.%m'))
        timeline_counts.append(count)
    
    # Данные для специалистов поддержки
    support_users = User.objects.filter(is_support=True)
    
    # Пагинация для пользователей
    users = User.objects.filter(is_admin=False, is_support=False).order_by('-date_joined')
    users_paginator = Paginator(users, 10)
    users_page = request.GET.get('users_page')
    users = users_paginator.get_page(users_page)
    
    # Пагинация для специалистов поддержки
    support_users_list = User.objects.filter(is_support=True).order_by('-date_joined')
    support_paginator = Paginator(support_users_list, 10)
    support_page = request.GET.get('support_page')
    support_users_paginated = support_paginator.get_page(support_page)
    
    # Пагинация для заявок
    tickets = Ticket.objects.all().order_by('-created_at')
    tickets_paginator = Paginator(tickets, 10)
    tickets_page = request.GET.get('tickets_page')
    tickets = tickets_paginator.get_page(tickets_page)
    
    return render(request, 'admin/admin_panel.html', {
        'total_tickets': total_tickets,
        'open_tickets': open_tickets,
        'in_progress_tickets': in_progress_tickets,
        'closed_tickets': closed_tickets,
        'total_users': total_users,
        'total_support': total_support,
        'total_categories': total_categories,
        'categories': categories,
        'timeline_dates': timeline_dates,
        'timeline_counts': timeline_counts,
        'support_users': support_users,
        'users': users,
        'support_users_paginated': support_users_paginated,
        'tickets': tickets,
    })


@login_required
@admin_required
def create_user(request):
    """Создание нового пользователя"""
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Пользователь успешно создан.')
            return redirect('admin_panel')
    else:
        form = UserForm()
    
    return render(request, 'admin/create_user.html', {
        'form': form,
    })


@login_required
@admin_required
def edit_user(request, user_id):
    """Редактирование пользователя"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Пользователь успешно обновлен.')
            return redirect('admin_panel')
    else:
        form = UserForm(instance=user)
    
    return render(request, 'admin/edit_user.html', {
        'form': form,
        'user_obj': user,
    })


@login_required
@admin_required
def delete_user(request, user_id):
    """Удаление пользователя"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'Пользователь успешно удален.')
        return redirect('admin_panel')
    
    return render(request, 'admin/delete_user.html', {
        'user_obj': user,
    })


@login_required
@admin_required
def create_support(request):
    """Создание нового специалиста поддержки"""
    if request.method == 'POST':
        form = SupportUserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_support = True
            user.save()
            
            # Сохраняем категории
            categories = form.cleaned_data['categories']
            user.categories.set(categories)
            
            messages.success(request, 'Специалист поддержки успешно создан.')
            return redirect('admin_panel')
    else:
        form = SupportUserForm()
    
    return render(request, 'admin/create_support.html', {
        'form': form,
    })


@login_required
@admin_required
def edit_support(request, user_id):
    """Редактирование специалиста поддержки"""
    user = get_object_or_404(User, id=user_id, is_support=True)
    
    if request.method == 'POST':
        form = SupportUserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Специалист поддержки успешно обновлен.')
            return redirect('admin_panel')
    else:
        form = SupportUserForm(instance=user)
    
    return render(request, 'admin/edit_support.html', {
        'form': form,
        'user_obj': user,
    })


@login_required
@admin_required
def delete_support(request, user_id):
    """Удаление специалиста поддержки"""
    user = get_object_or_404(User, id=user_id, is_support=True)
    
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'Специалист поддержки успешно удален.')
        return redirect('admin_panel')
    
    return render(request, 'admin/delete_support.html', {
        'user_obj': user,
    })


@login_required
@admin_required
def create_category(request):
    """Создание нового раздела"""
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Раздел успешно создан.')
            return redirect('admin_panel')
    else:
        form = CategoryForm()
    
    return render(request, 'admin/create_category.html', {
        'form': form,
    })


@login_required
@admin_required
def edit_category(request, category_id):
    """Редактирование раздела"""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Раздел успешно обновлен.')
            return redirect('admin_panel')
    else:
        form = CategoryForm(instance=category)
    
    return render(request, 'admin/edit_category.html', {
        'form': form,
        'category': category,
    })


@login_required
@admin_required
def delete_category(request, category_id):
    """Удаление раздела"""
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Раздел успешно удален.')
        return redirect('admin_panel')
    
    return render(request, 'admin/delete_category.html', {
        'category': category,
    })


@login_required
@admin_required
def delete_ticket(request, ticket_id):
    """Удаление заявки"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    if request.method == 'POST':
        ticket.delete()
        messages.success(request, 'Заявка успешно удалена.')
        return redirect('admin_tickets')
    
    return render(request, 'admin/delete_ticket.html', {
        'ticket': ticket,
    })


@login_required
def profile(request):
    """Профиль пользователя"""
    user = request.user
    
    if request.method == 'POST':
        form = UserForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен.')
            return redirect('profile')
    else:
        form = UserForm(instance=user)
    
    return render(request, 'profile.html', {
        'form': form,
    })


@login_required
def notifications(request):
    """Уведомления пользователя"""
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Отмечаем все уведомления как прочитанные
    notifications.filter(is_read=False).update(is_read=True)
    
    # Пагинация
    paginator = Paginator(notifications, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'notifications.html', {
        'notifications': page_obj,
    })


def faq(request):
    """Страница FAQ"""
    categories = Category.objects.all()
    faqs = FAQ.objects.all().order_by('category', 'order')
    
    return render(request, 'faq.html', {
        'categories': categories,
        'faqs': faqs,
    })


def knowledge_base(request):
    """База знаний"""
    categories = Category.objects.all()
    
    category_id = request.GET.get('category')
    if category_id:
        articles = KnowledgeBase.objects.filter(category_id=category_id).order_by('-updated_at')
    else:
        articles = KnowledgeBase.objects.all().order_by('-updated_at')
    
    # Поиск
    search = request.GET.get('search')
    if search:
        articles = articles.filter(
            Q(title__icontains=search) | 
            Q(content__icontains=search)
        )
    
    # Пагинация
    paginator = Paginator(articles, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'knowledge_base.html', {
        'categories': categories,
        'articles': page_obj,
    })


def knowledge_base_article(request, article_id):
    """Просмотр статьи базы знаний"""
    article = get_object_or_404(KnowledgeBase, id=article_id)
    
    return render(request, 'knowledge_base_article.html', {
        'article': article,
    })


@login_required
@admin_required
def create_faq(request):
    """Создание нового FAQ"""
    if request.method == 'POST':
        form = FAQForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'FAQ успешно создан.')
            return redirect('faq')
    else:
        form = FAQForm()
    
    return render(request, 'admin/create_faq.html', {
        'form': form,
    })


@login_required
@admin_required
def edit_faq(request, faq_id):
    """Редактирование FAQ"""
    faq = get_object_or_404(FAQ, id=faq_id)
    
    if request.method == 'POST':
        form = FAQForm(request.POST, instance=faq)
        if form.is_valid():
            form.save()
            messages.success(request, 'FAQ успешно обновлен.')
            return redirect('faq')
    else:
        form = FAQForm(instance=faq)
    
    return render(request, 'admin/edit_faq.html', {
        'form': form,
        'faq': faq,
    })


@login_required
@admin_required
def delete_faq(request, faq_id):
    """Удаление FAQ"""
    faq = get_object_or_404(FAQ, id=faq_id)
    
    if request.method == 'POST':
        faq.delete()
        messages.success(request, 'FAQ успешно удален.')
        return redirect('faq')
    
    return render(request, 'admin/delete_faq.html', {
        'faq': faq,
    })


@login_required
@admin_required
def create_knowledge_base(request):
    """Создание новой статьи базы знаний"""
    if request.method == 'POST':
        form = KnowledgeBaseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Статья успешно создана.')
            return redirect('knowledge_base')
    else:
        form = KnowledgeBaseForm()
    
    return render(request, 'admin/create_knowledge_base.html', {
        'form': form,
    })


@login_required
@admin_required
def edit_knowledge_base(request, article_id):
    """Редактирование статьи базы знаний"""
    article = get_object_or_404(KnowledgeBase, id=article_id)
    
    if request.method == 'POST':
        form = KnowledgeBaseForm(request.POST, instance=article)
        if form.is_valid():
            form.save()
            messages.success(request, 'Статья успешно обновлена.')
            return redirect('knowledge_base')
    else:
        form = KnowledgeBaseForm(instance=article)
    
    return render(request, 'admin/edit_knowledge_base.html', {
        'form': form,
        'article': article,
    })


@login_required
@admin_required
def delete_knowledge_base(request, article_id):
    """Удаление статьи базы знаний"""
    article = get_object_or_404(KnowledgeBase, id=article_id)
    
    if request.method == 'POST':
        article.delete()
        messages.success(request, 'Статья успешно удалена.')
        return redirect('knowledge_base')
    
    return render(request, 'admin/delete_knowledge_base.html', {
        'article': article,
    })