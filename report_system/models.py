from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

class Report(models.Model):
    REPORT_TYPES = (
        ('tickets', 'Отчет по заявкам'),
        ('support', 'Отчет по специалистам'),
        ('users', 'Отчет по пользователям'),
        ('general', 'Общий отчет'),
    )
    
    name = models.CharField(max_length=100, verbose_name='Название отчета')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES, verbose_name='Тип отчета')
    description = models.TextField(verbose_name='Описание')
    parameters = models.JSONField(default=dict, verbose_name='Параметры отчета')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Создал')
    
    class Meta:
        verbose_name = 'Отчет'
        verbose_name_plural = 'Отчеты'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_report_type_display()} - {self.name}"

class ReportData(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='data', verbose_name='Отчет')
    data = models.JSONField(verbose_name='Данные отчета')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    
    class Meta:
        verbose_name = 'Данные отчета'
        verbose_name_plural = 'Данные отчетов'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Данные отчета {self.report.name} от {self.created_at.strftime('%d.%m.%Y %H:%M')}"
