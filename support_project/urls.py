from django.contrib import admin
from django.urls import path, include
from support_system import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Админ-панель Django
    path('admin/', admin.site.urls),
    
    path('', views.index, name='index'),
    
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('notifications/', views.notifications, name='notifications'),
    path('notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    
    # Заявки пользователей
    path('tickets/', views.user_tickets, name='user_tickets'),
    path('tickets/create/', views.create_ticket, name='create_ticket'),
    path('tickets/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:ticket_id>/reply/', views.reply_ticket, name='reply_ticket'),
    path('tickets/<int:ticket_id>/status/', views.update_ticket_status, name='update_ticket_status'),
    path('tickets/<int:ticket_id>/rate/', views.rate_specialist, name='rate_specialist'),
    
    # Страницы специалистов поддержки
    path('support/', views.support_tickets, name='support_tickets'),
    path('support/new/', views.support_tickets, {'filter': 'new'}, name='new_tickets'),
    path('support/awaiting/', views.support_tickets, {'filter': 'awaiting'}, name='awaiting_response'),
    path('support/take/<int:ticket_id>/', views.take_ticket, name='take_ticket'),
    
    # Управление специалистами поддержки
    path('support-management/', views.support_users, name='support_users'),
    path('support-management/create/', views.create_support, name='create_support'),
    path('support-management/<int:user_id>/edit/', views.edit_support, name='edit_support'),
    path('support-management/<int:user_id>/delete/', views.delete_support, name='delete_support'),
    path('support-management/<int:user_id>/categories/', views.get_support_categories, name='get_support_categories'),
    
    # FAQ и база знаний
    path('faq/', views.faq, name='faq'),
    path('knowledge-base/', views.knowledge_base, name='knowledge_base'),
    path('knowledge-base/<int:article_id>/', views.knowledge_base_article, name='knowledge_base_article'),
    
    # Отчеты
    path('reports/', include('report_system.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)