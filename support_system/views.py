from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from datetime import timedelta
from .models import User, Category, Ticket, TicketMessage, FAQ, KnowledgeBase, Notification, TicketFile, MessageFile
from .forms import UserRegistrationForm, UserLoginForm, UserForm, SupportUserForm, CategoryForm, TicketForm, TicketMessageForm, FAQForm, KnowledgeBaseForm

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
                return redirect('dashboard')
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
            return redirect('dashboard')
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
    return render(request, 'support_system/dashboard.html', {
        'user_tickets': user_tickets,
        'support_tickets': support_tickets
    })

@login_required
def profile(request):
    """Профиль пользователя"""
    return render(request, 'support_system/profile.html')

@login_required
def notifications(request):
    """Уведомления пользователя"""
    notifications = request.user.notifications.filter(is_read=False)
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
    tickets = Ticket.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'support_system/tickets/list.html', {'tickets': tickets})

@login_required
def create_ticket(request):
    """Создание новой заявки"""
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.status = 'open'
            ticket.save()
            
            # Создаем уведомление для администраторов
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
    messages = ticket.messages.all().order_by('created_at')
    return render(request, 'support_system/tickets/detail.html', {
        'ticket': ticket,
        'messages': messages
    })

@login_required
def reply_ticket(request, ticket_id):
    """Ответ на заявку"""
    ticket = get_object_or_404(Ticket, id=ticket_id)
    
    # Проверяем права доступа
    if not (request.user == ticket.user or request.user == ticket.support_user or request.user.is_admin):
        messages.error(request, 'У вас нет прав для ответа на эту заявку')
        return redirect('ticket_detail', ticket_id=ticket.id)
    
    if request.method == 'POST':
        message = TicketMessage(
            ticket=ticket,
            user=request.user,
            content=request.POST.get('text', '')
        )
        
        if 'file' in request.FILES:
            message.file = request.FILES['file']
        
        message.save()
        
        # Если ответил специалист поддержки, меняем статус на "в работе"
        if request.user == ticket.support_user and ticket.status == 'open':
            ticket.status = 'in_progress'
            ticket.save()
        
        # Создаем уведомление для получателя
        recipient = ticket.user if request.user == ticket.support_user else ticket.support_user
        if recipient:
            Notification.objects.create(
                user=recipient,
                ticket=ticket,
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
    if not request.user.is_support and not request.user.is_support_specialist:
        return JsonResponse({'error': 'Недостаточно прав'}, status=403)
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не поддерживается'}, status=405)
    
    ticket = get_object_or_404(Ticket, id=ticket_id)
    status = request.POST.get('status')
    
    # Проверяем, что статус допустимый
    if status not in dict(Ticket.STATUS_CHOICES):
        return JsonResponse({'error': 'Неверный статус'}, status=400)
    
    # Проверяем права на изменение
    if ticket.support_user != request.user and not request.user.is_admin:
        return JsonResponse({'error': 'Вы не можете изменять статус этой заявки'}, status=403)
    
    # Сохраняем предыдущий статус для уведомления
    old_status = ticket.status
    
    # Обновляем статус
    ticket.status = status
    ticket.save()
    
    # Создаем уведомление для пользователя
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
def support_tickets(request, filter=None):
    """Список заявок для специалиста поддержки"""
    if not request.user.is_support and not request.user.is_support_specialist:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('dashboard')
    
    # Базовый QuerySet для заявок
    tickets = Ticket.objects.all()
    
    if filter == 'new':
        # Новые заявки (без назначенного специалиста) из категорий специалиста
        tickets = tickets.filter(
            Q(category__support_users=request.user) |  # Заявки из категорий специалиста
            Q(support_user=request.user)  # Или уже назначенные специалисту
        ).filter(
            Q(status='open') |  # Открытые заявки
            Q(status='in_progress', support_user=request.user)  # Или в работе у текущего специалиста
        ).distinct()
    elif filter == 'awaiting':
        # Заявки, ожидающие ответа более 24 часов
        day_ago = timezone.now() - timedelta(days=1)
        tickets = tickets.filter(
            support_user=request.user,
            status='in_progress'
        ).filter(
            Q(messages__isnull=True) |  # Нет сообщений
            Q(messages__created_at__lt=day_ago)  # Последнее сообщение старше 24 часов
        ).distinct()
    else:
        # Все заявки, доступные специалисту
        tickets = tickets.filter(
            Q(category__support_users=request.user) |  # Заявки из категорий специалиста
            Q(support_user=request.user)  # Или уже назначенные специалисту
        ).distinct()
    
    tickets = tickets.order_by('-created_at')
    
    return render(request, 'support_system/support/tickets.html', {
        'tickets': tickets,
        'filter': filter
    })

@login_required
def admin_panel(request):
    """Админ-панель"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('dashboard')
    return render(request, 'support_system/admin/panel.html')

@login_required
def admin_tickets(request):
    """Управление заявками в админ-панели"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('dashboard')
    tickets = Ticket.objects.all().order_by('-created_at')
    return render(request, 'support_system/admin/tickets.html', {'tickets': tickets})

@login_required
def assign_ticket(request, ticket_id):
    """Назначение заявки специалисту поддержки"""
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
    """Удаление заявки"""
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
    """Редактирование пользователя в админ-панели"""
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
    """Удаление пользователя"""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Недостаточно прав'}, status=403)
    
    user = get_object_or_404(User, id=user_id)
    user.delete()
    return JsonResponse({'status': 'success'})

# Управление специалистами поддержки
@login_required
def create_support(request):
    """Создание специалиста поддержки"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('dashboard')
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_support = True
            user.save()
            return redirect('admin_support')
    else:
        form = UserRegistrationForm()
    return render(request, 'support_system/admin/support_form.html', {'form': form})

@login_required
def edit_support(request, user_id):
    """Редактирование специалиста поддержки"""
    if not request.user.is_admin:
        messages.error(request, 'У вас нет доступа к этой странице')
        return redirect('dashboard')
    user = get_object_or_404(User, id=user_id, is_support=True)
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            return redirect('admin_support')
    else:
        form = UserRegistrationForm(instance=user)
    return render(request, 'support_system/admin/support_form.html', {'form': form})

@login_required
def delete_support(request, user_id):
    """Удаление специалиста поддержки"""
    if not request.user.is_admin:
        return JsonResponse({'error': 'Недостаточно прав'}, status=403)
    
    user = get_object_or_404(User, id=user_id, is_support=True)
    user.delete()
    return JsonResponse({'status': 'success'})

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
    
    # Проверяем, что заявка не назначена другому специалисту
    if ticket.support_user is not None:
        return JsonResponse({'error': 'Заявка уже назначена другому специалисту'}, status=400)
    
    # Проверяем, что специалист может работать с этой категорией
    if request.user not in ticket.category.support_users.all():
        return JsonResponse({'error': 'Вы не можете работать с заявками этой категории'}, status=403)
    
    try:
        # Назначаем заявку специалисту
        ticket.support_user = request.user
        ticket.status = 'in_progress'
        ticket.save()
        
        # Создаем уведомление для пользователя
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
    """Контекстный процессор для добавления счетчиков уведомлений"""
    context = {}
    
    if request.user.is_authenticated:
        if request.user.is_support:
            # Новые заявки из категорий специалиста
            context['new_tickets_count'] = Ticket.objects.filter(
                category__support_users=request.user,
                support_user__isnull=True,
                status='open'
            ).count()
            
            # Заявки, ожидающие ответа более 24 часов
            day_ago = timezone.now() - timedelta(days=1)
            context['waiting_response_count'] = Ticket.objects.filter(
                support_user=request.user,
                status='in_progress'
            ).filter(
                Q(messages__isnull=True) |  # Нет сообщений
                Q(messages__created_at__lt=day_ago)  # Последнее сообщение старше 24 часов
            ).distinct().count()
        else:
            # Обычные уведомления для пользователей
            context['notifications_count'] = request.user.notifications.filter(
                is_read=False
            ).count()
    
    return context
