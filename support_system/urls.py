from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile, name='profile'),
    path('notifications/', views.notifications, name='notifications'),
    path('faq/', views.faq, name='faq'),
    path('knowledge-base/', views.knowledge_base, name='knowledge_base'),
    path('knowledge-base/<int:article_id>/', views.knowledge_base_article, name='knowledge_base_article'),
    
    # Заявки
    path('tickets/', views.user_tickets, name='user_tickets'),
    path('tickets/create/', views.create_ticket, name='create_ticket'),
    path('tickets/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('tickets/<int:ticket_id>/reply/', views.reply_ticket, name='reply_ticket'),
    path('tickets/<int:ticket_id>/status/', views.update_ticket_status, name='update_ticket_status'),
    path('tickets/<int:ticket_id>/take/', views.take_ticket, name='take_ticket'),
    
    # Специалисты поддержки
    path('support/', views.support_tickets, name='support_tickets'),
    
    # Админ-панель
    path('admin/panel/', views.admin_panel, name='admin_panel'),
    path('admin/tickets/', views.admin_tickets, name='admin_tickets'),
    path('admin/tickets/<int:ticket_id>/assign/', views.assign_ticket, name='assign_ticket'),
    path('admin/tickets/<int:ticket_id>/delete/', views.delete_ticket, name='delete_ticket'),
    
    # Управление пользователями
    path('admin/users/create/', views.create_user, name='create_user'),
    path('admin/users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('admin/users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    
    # Управление специалистами поддержки
    path('admin/support/create/', views.create_support, name='create_support'),
    path('admin/support/<int:user_id>/edit/', views.edit_support, name='edit_support'),
    path('admin/support/<int:user_id>/delete/', views.delete_support, name='delete_support'),
    
    # Управление разделами
    path('categories/', views.categories, name='categories'),
    path('categories/create/', views.create_category, name='create_category'),
    path('categories/<int:category_id>/edit/', views.edit_category, name='edit_category'),
    path('categories/<int:category_id>/delete/', views.delete_category, name='delete_category'),
    
    # Управление FAQ
    path('admin/faq/create/', views.create_faq, name='create_faq'),
    path('admin/faq/<int:faq_id>/edit/', views.edit_faq, name='edit_faq'),
    path('admin/faq/<int:faq_id>/delete/', views.delete_faq, name='delete_faq'),
    
    # Управление базой знаний
    path('admin/knowledge-base/create/', views.create_knowledge_base, name='create_knowledge_base'),
    path('admin/knowledge-base/<int:article_id>/edit/', views.edit_knowledge_base, name='edit_knowledge_base'),
    path('admin/knowledge-base/<int:article_id>/delete/', views.delete_knowledge_base, name='delete_knowledge_base'),
] 