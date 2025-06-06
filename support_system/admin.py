from django.contrib import admin
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from .models import User, Category, Ticket, TicketMessage, File, Content, Notification, FAQ, KnowledgeBase

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_support', 'is_admin')
    list_filter = ('is_support', 'is_admin', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    actions = ['make_support', 'remove_support']

    def make_support(self, request, queryset):
        updated = queryset.update(is_support=True)
        self.message_user(
            request,
            f'{updated} пользователей успешно назначены специалистами поддержки.',
            messages.SUCCESS
        )
    make_support.short_description = "Назначить специалистом поддержки"

    def remove_support(self, request, queryset):
        updated = queryset.update(is_support=False)
        self.message_user(
            request,
            f'У {updated} пользователей удален статус специалиста поддержки.',
            messages.SUCCESS
        )
    remove_support.short_description = "Удалить статус специалиста поддержки"

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'get_support_users_count', 'tickets_count')
    search_fields = ('name', 'description')
    filter_horizontal = ('support_users',)

    def get_support_users_count(self, obj):
        return obj.support_users.count()
    get_support_users_count.short_description = 'Специалисты поддержки'

@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'user', 'category', 'status', 'support_user', 'created_at')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('title', 'description', 'user__username', 'support_user__username')
    raw_id_fields = ('user', 'support_user', 'category')

@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'user', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('content', 'user__username')
    raw_id_fields = ('ticket', 'user')

@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('filename', 'content_type', 'object_id', 'uploaded_at')
    list_filter = ('content_type', 'uploaded_at')
    search_fields = ('filename',)
    date_hierarchy = 'uploaded_at'

@admin.register(Content)
class ContentAdmin(admin.ModelAdmin):
    list_display = ('title', 'type', 'category', 'order', 'updated_at')
    list_filter = ('type', 'category', 'updated_at')
    search_fields = ('title', 'content')
    ordering = ('category', 'order', '-updated_at')

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'order')
    search_fields = ('question', 'answer')
    ordering = ('order',)
    exclude = ('category',)

@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'updated_at')
    search_fields = ('title', 'content')
    ordering = ('-updated_at',)
    exclude = ('category',)
