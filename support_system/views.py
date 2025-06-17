from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count, Avg, Max, Subquery, OuterRef, F
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import secrets
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import timedelta
from .models import User, Category, Ticket, TicketMessage, File, Content, Notification, MessageFile, FAQ, KnowledgeBase, SupportRating
from .forms import (
    UserRegistrationForm, 
    UserLoginForm, 
    UserForm, 
    SupportUserForm, 
    CategoryForm, 
    TicketForm, 
    TicketMessageForm, 
    ContentForm,
    FAQForm,
    KnowledgeBaseForm,
    SupportRatingForm,
    UserProfileForm
)
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy

def index(request):
    """Главная страница"""
    return render(request, 'support_system/index.html')

def login_view(request):
    """Страница входа"""
    if request.method == 'POST':
        form = UserLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('index')
            else:
                messages.error(request, 'Неверное имя пользователя или пароль')
    else:
        form = UserLoginForm()
    return render(request, 'support_system/login.html', {'form': form})

def register_view(request):
    """Страница регистрации"""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('index')
    else:
        form = UserRegistrationForm()
    return render(request, 'support_system/register.html', {'form': form})

def logout_view(request):
    """Выход из системы"""
    logout(request)
    return redirect('login')

@login_required
def dashboard(request):
    """Панель управления"""
    user_tickets = Ticket.objects.filter(user=request.user).order_by('-created_at')[:5]
    if request.user.is_support:
        support_tickets = Ticket.objects.filter(support_user=request.user, status='open').order_by('-created_at')[:5]
    else:
        support_tickets = None
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
        tickets_count=Count('assigned_tickets', filter=Q(assigned_tickets__status='closed'), distinct=True)
    ).order_by('-avg_score', '-tickets_count')[:10]
    return render(request, 'support_system/dashboard.html', {
        'user_tickets': user_tickets,
        'support_tickets': support_tickets,
        'avg_rating': avg_rating,
        'ratings_count': ratings_count,
        'top_specialists': top_specialists,
        'specialists_rating': specialists_rating,
    })

@login_required
def profile(request):
    """Профиль пользователя"""
    user_profile = request.user

    if request.method == 'POST':
        if user_profile.is_admin:
            if 'generate_api_key' in request.POST:
                user_profile.api_key = secrets.token_hex(32)
                user_profile.save()
                messages.success(request, _('Новый API ключ успешно сгенерирован.'))
            elif 'delete_api_key' in request.POST:
                user_profile.api_key = None
                user_profile.save()
                messages.success(request, _('API ключ успешно удален.'))
        else:
            messages.error(request, _('У вас нет прав для выполнения этого действия.'))
        return redirect('profile')

    return render(request, 'support_system/profile.html', {
        'user_profile': user_profile, 
        'api_key': user_profile.api_key
    })

@login_required
def notifications(request):
    """Уведомления пользователя"""
    notifications = request.user.notifications.all().order_by('-created_at')
    return render(request, 'support_system/notifications.html', {'notifications': notifications})

def faq(request):
    """Страница FAQ"""
    faqs = FAQ.objects.all().order_by('category', 'order')
    return render(request, 'support_system/faq.html', {'faqs': faqs})

def knowledge_base(request):
    """База знаний"""
    articles = KnowledgeBase.objects.all()
    return render(request, 'support_system/knowledge_base.html', {'articles': articles})

def knowledge_base_article(request, article_id):
    """Статья базы знаний"""
    article = get_object_or_404(KnowledgeBase, id=article_id)
    return render(request, 'support_system/knowledge_base_article.html', {'article': article})

@login_required
def user_tickets(request):
    """Список заявок пользователя"""
    sort = request.GET.get('sort', '-created_at')
    status = request.GET.get('status')
    tickets = Ticket.objects.filter(user=request.user)
    if status:
        tickets = tickets.filter(status=status)
    tickets = tickets.order_by(sort)
    paginator = Paginator(tickets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'support_system/tickets/list.html', {
        'tickets': page_obj,
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    })

@login_required
def create_ticket(request):
    """Создание новой заявки"""
    if request.user.is_support:
        messages.error(request, 'Специалист поддержки не может создавать заявки.')
        return redirect('dashboard')
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.status = 'open'
            ticket.save()
            
            admins = User.objects.filter(is_admin=True)
            for admin in admins:
                Notification.objects.create(
                    user=admin,
                    ticket=ticket,
                    type='ticket_created',
                    text=f'Создана новая заявка #{ticket.id}'
                )
            
            messages.success(request, _('Заявка успешно создана'))
            return redirect('ticket_detail', ticket_id=ticket.id)
    else:
        form = TicketForm()
    
    return render(request, 'support_system/tickets/create.html', {
        'form': form,
        'categories': Category.objects.all()
    })

@login_required
def ticket_detail(request, ticket_id):
    """Детали заявки"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    if request.user != ticket.user and not request.user.is_support and not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этой заявке')
        return redirect('user_tickets')
    if request.user.is_support and ticket.status == 'open':
        ticket.status = 'in-progress'
        ticket.save()
    return render(request, 'support_system/tickets/detail.html', {
        'ticket': ticket
    })

@login_required
def reply_ticket(request, ticket_id):
    """Ответ на заявку"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    if not (request.user == ticket.user or request.user == ticket.support_user or request.user.is_admin):
        messages.error(request, 'У вас нет прав для ответа на эту заявку')
        return redirect('ticket_detail', ticket_id=ticket.id)
    
    if request.method == 'POST':
        content = request.POST.get('content', '').strip()
        if not content:
            messages.error(request, 'Нельзя отправить пустое сообщение.')
            return redirect('ticket_detail', ticket_id=ticket.id)
        message = TicketMessage(
            ticket=ticket,
            user=request.user,
            content=content
        )
        message.save()
        
        if 'files' in request.FILES:
            files = request.FILES.getlist('files')
            for file in files:
                MessageFile.objects.create(
                    message=message,
                    file=file,
                    filename=file.name
                )
        
        # Смена статуса на "в работе"
        if request.user == ticket.support_user and ticket.status == 'open':
            ticket.status = 'in-progress'
            ticket.save()
        
        # Уведомление специалиста о новом ответе пользователя
        if request.user == ticket.user and ticket.support_user:
            Notification.objects.create(
                user=ticket.support_user,
                ticket=ticket,
                message=message,
                type='message_created',
                text=f'Новый ответ в заявке #{ticket.id}'
            )
        elif request.user == ticket.support_user and ticket.user:
            Notification.objects.create(
                user=ticket.user,
                ticket=ticket,
                message=message,
                type='reply',
                text=f'Новый ответ в заявке #{ticket.id}'
            )
        
        messages.success(request, 'Ответ успешно отправлен')
        return redirect('ticket_detail', ticket_id=ticket.id)
    
    return render(request, 'support_system/tickets/detail.html', {
        'ticket': ticket
    })

@login_required
def update_ticket_status(request, ticket_id):
    """Обновление статуса заявки"""
    if not request.user.is_support and not request.user.is_support_specialist and not request.user.is_admin:
        return JsonResponse({'error': 'Недостаточно прав'}, status=403)
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)
    ticket = get_object_or_404(Ticket, id=ticket_id)
    status = request.POST.get('status')
    if status not in dict(Ticket.STATUS_CHOICES):
        return JsonResponse({'error': 'Неверный статус'}, status=400)
    old_status = ticket.status
    ticket.status = status
    ticket.save()
    if old_status != status:
        status_display = dict(Ticket.STATUS_CHOICES)[status]
        Notification.objects.create(
            user=ticket.user,
            ticket=ticket,
            type='status',
            text=f'Статус вашей заявки #{ticket.id} изменен на "{status_display}"'
        )
    return JsonResponse({
        'status': 'success',
        'new_status': status,
        'new_status_display': ticket.get_status_display()
    })

@login_required
def support_tickets(request):
    user = request.user
    filter_type = request.GET.get('filter')

    if user.is_admin:
        tickets_qs = Ticket.objects.all().order_by('-created_at')
        new_tickets = Ticket.objects.filter(support_user__isnull=True, status='open')
        last_msg_user = TicketMessage.objects.filter(ticket=OuterRef('pk')).order_by('-created_at').values('user')[:1]
        awaiting_tickets = Ticket.objects.filter(status='in-progress').annotate(
            last_msg_user=Subquery(last_msg_user)
        ).filter(
            last_msg_user__isnull=False
        ).exclude(
            last_msg_user=F('support_user')
        )
    else:
        new_tickets = Ticket.objects.filter(
            category__support_users=user,
            support_user__isnull=True,
            status='open'
        ).distinct()
        my_tickets = Ticket.objects.filter(support_user=user)
        last_msg_user = TicketMessage.objects.filter(ticket=OuterRef('pk')).order_by('-created_at').values('user')[:1]
        awaiting_tickets = Ticket.objects.filter(
            support_user=user,
            status='in-progress'
        ).annotate(
            last_msg_user=Subquery(last_msg_user)
        ).filter(
            last_msg_user__isnull=False
        ).exclude(
            last_msg_user=user.id
        )
        tickets_qs = Ticket.objects.filter(
            Q(support_user=user) | Q(category__support_users=user, support_user__isnull=True, status='open')
        ).distinct().order_by('-created_at')

    if filter_type == 'new':
        tickets = new_tickets.order_by('-created_at')
    elif filter_type == 'awaiting':
        tickets = awaiting_tickets.order_by('-created_at')
    else:
        tickets = tickets_qs

    paginator = Paginator(tickets, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'support_system/support/tickets.html', {
        'tickets': page_obj,
        'filter': filter_type,
        'new_tickets_count': new_tickets.count(),
        'awaiting_tickets_count': awaiting_tickets.count(),
        'is_paginated': page_obj.has_other_pages(),
        'page_obj': page_obj,
    })

@login_required
def admin_panel(request):
    if not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('dashboard')
    return render(request, 'support_system/admin/panel.html')

@login_required
def assign_ticket(request, ticket_id):
    if not request.user.is_admin:
        return JsonResponse({'error': 'Недостаточно прав'}, status=403)
    
    ticket = get_object_or_404(Ticket, id=ticket_id)
    support_user_id = request.POST.get('support_user_id')
    support_user = get_object_or_404(User, id=support_user_id, is_support=True)
    
    ticket.support_user = support_user
    ticket.save()
    return JsonResponse({'status': 'success'})

@login_required
def delete_ticket(request, ticket_id):
    if not request.user.is_admin:
        return JsonResponse({'error': 'Недостаточно прав'}, status=403)
    
    ticket = get_object_or_404(Ticket, id=ticket_id)
    ticket.delete()
    return JsonResponse({'status': 'success'})

# Управление пользователями
@login_required
def create_user(request):
    """Создание пользователя в админ-панели"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('dashboard')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin_users')
    else:
        form = UserRegistrationForm()
    return render(request, 'support_system/admin/user_form.html', {'form': form})

@login_required
def edit_user(request, user_id):
    if not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('dashboard')
    user = get_object_or_404(User, id=user_id)
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('admin_users')
    else:
        form = UserRegistrationForm(instance=user)
    return render(request, 'support_system/admin/user_form.html', {'form': form})

@login_required
def delete_user(request, user_id):
    if not request.user.is_admin:
        return JsonResponse({'error': 'Недостаточно прав'}, status=403)
    
    user = get_object_or_404(User, id=user_id)
    user.delete()
    return JsonResponse({'status': 'success'})

# Управление специалистами поддержки
@login_required
def support_users(request):
    """Список специалистов поддержки"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('dashboard')
    
    support_users = User.objects.filter(is_support=True).annotate(
        active_tickets_count=Count('assigned_tickets', filter=Q(assigned_tickets__status='in-progress'))
    )
    categories = Category.objects.all()
    
    return render(request, 'support_system/admin/support_users.html', {
        'support_users': support_users,
        'categories': categories
    })

@login_required
def create_support(request):
    if not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        category_ids = request.POST.getlist('categories')
        errors = {}
        if not username:
            errors['username'] = 'Пожалуйста, заполните имя пользователя.'
        if not email:
            errors['email'] = 'Пожалуйста, заполните email.'
        elif '@' not in email or '.' not in email:
            errors['email'] = 'Введите корректный email.'
        if not password:
            errors['password'] = 'Пожалуйста, введите пароль.'
        elif len(password) < 8:
            errors['password'] = 'Пароль должен быть не менее 8 символов.'
        if not category_ids:
            errors['categories'] = 'Выберите хотя бы одну категорию.'
        if errors:
            support_users = User.objects.filter(is_support=True).annotate(
                active_tickets_count=Count('assigned_tickets', filter=Q(assigned_tickets__status='in-progress'))
            )
            categories = Category.objects.all()
            return render(request, 'support_system/admin/support_users.html', {
                'support_users': support_users,
                'categories': categories,
                'form_errors': errors,
                'form_data': request.POST
            })
        try:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                is_support=True
            )
            user.categories.set(category_ids)
            messages.success(request, 'Специалист поддержки успешно создан')
            return redirect('support_users')
        except Exception as e:
            messages.error(request, f'Ошибка при создании специалиста: {str(e)}')
    
    return redirect('support_users')

@login_required
def edit_support(request, user_id):
    """Редактирование специалиста поддержки"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('dashboard')
    
    user = get_object_or_404(User, id=user_id, is_support=True)
    
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        category_ids = request.POST.getlist('categories')
        
        try:
            user.username = username
            user.email = email
            user.save()
            user.categories.set(category_ids)
            messages.success(request, 'Данные специалиста успешно обновлены')
        except Exception as e:
            messages.error(request, f'Ошибка при обновлении данных: {str(e)}')
    
    return redirect('support_users')

@login_required
def delete_support(request, user_id):
    """Удаление специалиста поддержки"""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Недостаточно прав'}, status=403)
    
    user = get_object_or_404(User, id=user_id, is_support=True)
    
    try:
        user.delete()
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def get_support_categories(request, user_id):
    """Получение категорий специалиста поддержки"""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Недостаточно прав'}, status=403)
    
    user = get_object_or_404(User, id=user_id, is_support=True)
    categories = list(user.categories.values_list('id', flat=True))
    
    return JsonResponse({'categories': categories})

# Управление разделами
@login_required
def categories(request):
    """Список разделов"""
    categories = Category.objects.all()
    return render(request, 'support_system/categories/list.html', {
        'categories': categories
    })

@login_required
def create_category(request):
    """Создание нового раздела"""
    if not request.user.is_admin:
        messages.error(request, _('У вас нет прав для создания разделов'))
        return redirect('categories')
    
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, _('Раздел успешно создан'))
            return redirect('categories')
    else:
        form = CategoryForm()
    
    return render(request, 'support_system/categories/form.html', {
        'form': form,
        'title': _('Создание раздела')
    })

@login_required
def edit_category(request, category_id):
    """Редактирование раздела"""
    if not request.user.is_admin:
        messages.error(request, _('У вас нет прав для редактирования разделов'))
        return redirect('categories')
    
    category = get_object_or_404(Category, id=category_id)
    
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, _('Раздел успешно обновлен'))
            return redirect('categories')
    else:
        form = CategoryForm(instance=category)
    
    return render(request, 'support_system/categories/form.html', {
        'form': form,
        'title': _('Редактирование раздела'),
        'category': category
    })

@login_required
def delete_category(request, category_id):
    """Удаление раздела"""
    if not request.user.is_admin:
        return JsonResponse({'error': _('У вас нет прав для удаления разделов')}, status=403)
    
    category = get_object_or_404(Category, id=category_id)
    category.delete()
    
    return JsonResponse({'success': True})

# Управление FAQ
@login_required
def create_faq(request):
    """Создание FAQ"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('dashboard')
    if request.method == 'POST':
        form = FAQForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin_faq')
    else:
        form = FAQForm()
    return render(request, 'support_system/admin/faq_form.html', {'form': form})

@login_required
def edit_faq(request, faq_id):
    """Редактирование FAQ"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('dashboard')
    faq = get_object_or_404(FAQ, id=faq_id)
    if request.method == 'POST':
        form = FAQForm(request.POST, instance=faq)
        if form.is_valid():
            form.save()
            return redirect('admin_faq')
    else:
        form = FAQForm(instance=faq)
    return render(request, 'support_system/admin/faq_form.html', {'form': form})

@login_required
def delete_faq(request, faq_id):
    """Удаление FAQ"""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Недостаточно прав'}, status=403)
    
    faq = get_object_or_404(FAQ, id=faq_id)
    faq.delete()
    return JsonResponse({'status': 'success'})

# Управление базой знаний
@login_required
def create_knowledge_base(request):
    """Создание статьи базы знаний"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('dashboard')
    if request.method == 'POST':
        form = KnowledgeBaseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('admin_knowledge_base')
    else:
        form = KnowledgeBaseForm()
    return render(request, 'support_system/admin/knowledge_base_form.html', {'form': form})

@login_required
def edit_knowledge_base(request, article_id):
    """Редактирование статьи базы знаний"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('dashboard')
    article = get_object_or_404(KnowledgeBase, id=article_id)
    if request.method == 'POST':
        form = KnowledgeBaseForm(request.POST, instance=article)
        if form.is_valid():
            form.save()
            return redirect('admin_knowledge_base')
    else:
        form = KnowledgeBaseForm(instance=article)
    return render(request, 'support_system/admin/knowledge_base_form.html', {'form': form})

@login_required
def delete_knowledge_base(request, article_id):
    """Удаление статьи базы знаний"""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Недостаточно прав'}, status=403)
    
    article = get_object_or_404(KnowledgeBase, id=article_id)
    article.delete()
    return JsonResponse({'status': 'success'})

@login_required
@require_POST
def take_ticket(request, ticket_id):
    """Принятие заявки в работу специалистом поддержки"""
    if not request.user.is_support and not request.user.is_support_specialist:
        return JsonResponse({'error': 'Недостаточно прав'}, status=403)
    
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    if ticket.support_user is not None:
        return JsonResponse({'error': 'Заявка уже назначена другому специалисту'}, status=400)
    
    if request.user not in ticket.category.support_users.all():
        return JsonResponse({'error': 'Вы не можете работать с заявками этой категории'}, status=403)
    
    try:
        ticket.support_user = request.user
        ticket.status = 'in-progress'
        ticket.save()
        
        Notification.objects.create(
            user=ticket.user,
            ticket=ticket,
            type='ticket_assigned',
            text=f'Ваша заявка #{ticket.id} принята в работу'
        )
        
        messages.success(request, f'Заявка #{ticket.id} принята в работу')
        return JsonResponse({
            'status': 'success',
            'message': f'Заявка #{ticket.id} принята в работу'
        })
    except Exception as e:
        return JsonResponse({
            'error': str(e)
        }, status=500)

def notifications_processor(request):
    """Контекстный процессор для добавления уведомлений и их количества, а также новых заявок для саппортов"""
    context = {}
    if request.user.is_authenticated:
        notifications_qs = request.user.notifications.filter(is_read=False).order_by('-created_at')
        context['notifications'] = notifications_qs[:5]
        context['notifications_count'] = notifications_qs.count()
        if request.user.is_support:
            new_tickets_count = Ticket.objects.filter(
                category__support_users=request.user,
                support_user__isnull=True,
                status='open'
            ).count()
            context['new_tickets_count'] = new_tickets_count
            day_ago = timezone.now() - timedelta(days=1)
            context['waiting_response_count'] = Ticket.objects.filter(
                support_user=request.user,
                status='in-progress'
            ).filter(
                Q(messages__isnull=True) |
                Q(messages__created_at__lt=day_ago)
            ).distinct().count()
    return context

@login_required
def mark_all_notifications_read(request):
    """Отметить все уведомления как прочитанные"""
    if request.method == 'POST':
        request.user.notifications.update(is_read=True)
        messages.success(request, 'Все уведомления отмечены как прочитанные')
    return redirect('notifications')

@login_required
def rate_specialist(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id, user=request.user, status='closed')
    if hasattr(ticket, 'rating'):
        return render(request, 'support_system/tickets/already_rated.html', {'ticket': ticket})
    if request.method == 'POST':
        form = SupportRatingForm(request.POST)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.ticket = ticket
            rating.specialist = ticket.support_user
            rating.user = request.user
            rating.save()
            return render(request, 'support_system/tickets/thanks_for_rating.html', {'ticket': ticket})
    else:
        form = SupportRatingForm()
    return render(request, 'support_system/tickets/rate_specialist.html', {'form': form, 'ticket': ticket})

def reports_dashboard(request):
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
        tickets_count=Count('assigned_tickets', filter=Q(assigned_tickets__status='closed'), distinct=True)
    ).order_by('-avg_score', '-tickets_count')[:10]
    context = {
        'avg_rating': avg_rating,
        'ratings_count': ratings_count,
        'top_specialists': top_specialists,
        'specialists_rating': specialists_rating,
    }
    return render(request, 'report_system/dashboard.html', context)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ваш профиль успешно обновлен.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    return render(request, 'support_system/edit_profile.html', {'form': form})
