import os
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class User(AbstractUser):
    """Расширенная модель пользователя"""
    is_support = models.BooleanField(default=False, verbose_name=_('Специалист поддержки'))
    is_admin = models.BooleanField(default=False, verbose_name=_('Администратор'))
    phone = models.CharField(max_length=20, blank=True, null=True, verbose_name=_('Телефон'))
    
    class Meta:
        verbose_name = _('Пользователь')
        verbose_name_plural = _('Пользователи')
    
    def __str__(self):
        return self.username


class Category(models.Model):
    """Модель для разделов (категорий) заявок"""
    name = models.CharField(max_length=100, verbose_name=_('Название'))
    description = models.TextField(blank=True, null=True, verbose_name=_('Описание'))
    support_users = models.ManyToManyField(User, related_name='categories', blank=True, verbose_name=_('Специалисты поддержки'))
    
    class Meta:
        verbose_name = _('Раздел')
        verbose_name_plural = _('Разделы')
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    @property
    def tickets_count(self):
        return self.tickets.count()


class Ticket(models.Model):
    """Модель для заявок (тикетов)"""
    STATUS_CHOICES = (
        ('open', _('Открыт')),
        ('in-progress', _('В процессе')),
        ('closed', _('Закрыт')),
    )
    
    title = models.CharField(max_length=200, verbose_name=_('Тема'))
    description = models.TextField(verbose_name=_('Описание'))
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tickets', verbose_name=_('Пользователь'))
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='tickets', verbose_name=_('Раздел'))
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open', verbose_name=_('Статус'))
    support_user = models.ForeignKey(User, on_delete=models.SET_NULL, related_name='assigned_tickets', null=True, blank=True, verbose_name=_('Специалист поддержки'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))
    
    class Meta:
        verbose_name = _('Заявка')
        verbose_name_plural = _('Заявки')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"#{self.id} - {self.title}"


class TicketMessage(models.Model):
    """Модель для сообщений в заявке"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='messages', verbose_name=_('Заявка'))
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_('Пользователь'))
    content = models.TextField(verbose_name=_('Сообщение'), blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    
    class Meta:
        verbose_name = _('Сообщение')
        verbose_name_plural = _('Сообщения')
        ordering = ['created_at']
    
    def __str__(self):
        return f"Сообщение от {self.user} в заявке #{self.ticket.id}"


def ticket_file_path(instance, filename):
    """Функция для определения пути сохранения файлов заявок"""
    return f"tickets/{instance.ticket.id}/{filename}"


def message_file_path(instance, filename):
    """Функция для определения пути сохранения файлов сообщений"""
    return f"tickets/{instance.message.ticket.id}/messages/{instance.message.id}/{filename}"


class TicketFile(models.Model):
    """Модель для файлов, прикрепленных к заявке"""
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='files', verbose_name=_('Заявка'))
    file = models.FileField(upload_to=ticket_file_path, verbose_name=_('Файл'))
    filename = models.CharField(max_length=255, verbose_name=_('Имя файла'))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата загрузки'))
    
    class Meta:
        verbose_name = _('Файл заявки')
        verbose_name_plural = _('Файлы заявок')
    
    def __str__(self):
        return self.filename
    
    def save(self, *args, **kwargs):
        if not self.filename:
            self.filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)


class MessageFile(models.Model):
    """Модель для файлов, прикрепленных к сообщениям"""
    message = models.ForeignKey(TicketMessage, on_delete=models.CASCADE, related_name='files', verbose_name=_('Сообщение'))
    file = models.FileField(upload_to=message_file_path, verbose_name=_('Файл'))
    filename = models.CharField(max_length=255, verbose_name=_('Имя файла'))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата загрузки'))
    
    class Meta:
        verbose_name = _('Файл сообщения')
        verbose_name_plural = _('Файлы сообщений')
    
    def __str__(self):
        return self.filename
    
    def save(self, *args, **kwargs):
        if not self.filename:
            self.filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)


class Notification(models.Model):
    """Модель для уведомлений"""
    TYPE_CHOICES = (
        ('ticket_created', _('Создана новая заявка')),
        ('ticket_updated', _('Заявка обновлена')),
        ('ticket_assigned', _('Заявка назначена')),
        ('message_created', _('Новое сообщение')),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name=_('Пользователь'))
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Заявка'))
    message = models.ForeignKey(TicketMessage, on_delete=models.CASCADE, null=True, blank=True, verbose_name=_('Сообщение'))
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name=_('Тип'))
    text = models.CharField(max_length=255, verbose_name=_('Текст'))
    is_read = models.BooleanField(default=False, verbose_name=_('Прочитано'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    
    class Meta:
        verbose_name = _('Уведомление')
        verbose_name_plural = _('Уведомления')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Уведомление для {self.user}: {self.text}"


class File(models.Model):
    """Универсальная модель для файлов"""
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    file = models.FileField(upload_to='files/', verbose_name=_('Файл'))
    filename = models.CharField(max_length=255, verbose_name=_('Имя файла'))
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата загрузки'))
    
    class Meta:
        verbose_name = _('Файл')
        verbose_name_plural = _('Файлы')
    
    def __str__(self):
        return self.filename
    
    def save(self, *args, **kwargs):
        if not self.filename:
            self.filename = os.path.basename(self.file.name)
        super().save(*args, **kwargs)


class Content(models.Model):
    """Универсальная модель для контента (FAQ и База знаний)"""
    CONTENT_TYPES = (
        ('faq', _('FAQ')),
        ('kb', _('База знаний')),
    )
    
    type = models.CharField(max_length=10, choices=CONTENT_TYPES, verbose_name=_('Тип контента'))
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='contents', verbose_name=_('Раздел'))
    title = models.CharField(max_length=255, verbose_name=_('Заголовок'))
    content = models.TextField(verbose_name=_('Содержание'))
    order = models.PositiveIntegerField(default=0, verbose_name=_('Порядок'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))
    
    class Meta:
        verbose_name = _('Контент')
        verbose_name_plural = _('Контент')
        ordering = ['category', 'order', '-updated_at']
    
    def __str__(self):
        return self.title


class FAQ(models.Model):
    """Модель для часто задаваемых вопросов"""
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='faqs', verbose_name=_('Раздел'), null=True, blank=True)
    question = models.CharField(max_length=255, verbose_name=_('Вопрос'))
    answer = models.TextField(verbose_name=_('Ответ'))
    order = models.PositiveIntegerField(default=0, verbose_name=_('Порядок'))
    
    class Meta:
        verbose_name = _('FAQ')
        verbose_name_plural = _('FAQ')
        ordering = ['category', 'order']
    
    def __str__(self):
        return self.question


class KnowledgeBase(models.Model):
    """Модель для базы знаний"""
    title = models.CharField(max_length=255, verbose_name=_('Заголовок'))
    content = models.TextField(verbose_name=_('Содержание'))
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='knowledge_base', verbose_name=_('Раздел'), null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата создания'))
    updated_at = models.DateTimeField(auto_now=True, verbose_name=_('Дата обновления'))
    
    class Meta:
        verbose_name = _('База знаний')
        verbose_name_plural = _('База знаний')
        ordering = ['-updated_at']
    
    def __str__(self):
        return self.title


class SupportRating(models.Model):
    ticket = models.OneToOneField('Ticket', on_delete=models.CASCADE, related_name='rating', verbose_name=_('Заявка'))
    specialist = models.ForeignKey(User, on_delete=models.CASCADE, related_name='specialist_ratings', verbose_name=_('Специалист'))
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_ratings', verbose_name=_('Оценивший пользователь'))
    score = models.PositiveSmallIntegerField(choices=[(i, f'{i} звёзд') for i in range(1, 6)], verbose_name=_('Оценка'))
    comment = models.TextField(blank=True, verbose_name=_('Комментарий'))
    created_at = models.DateTimeField(auto_now_add=True, verbose_name=_('Дата оценки'))

    class Meta:
        verbose_name = _('Оценка специалиста')
        verbose_name_plural = _('Оценки специалистов')
        ordering = ['-created_at']

    def __str__(self):
        return f'Оценка {self.score} для заявки #{self.ticket.id}'
