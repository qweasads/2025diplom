from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _

from .models import User, Ticket, TicketMessage, Category, FAQ, KnowledgeBase


class UserRegistrationForm(UserCreationForm):
    """Форма регистрации пользователя"""
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'first_name', 'last_name', 'phone')


class UserLoginForm(forms.Form):
    """Форма входа"""
    username = forms.CharField(label='Имя пользователя')
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)


class UserForm(forms.ModelForm):
    """Форма для пользователя"""
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'is_active')


class SupportUserForm(forms.ModelForm):
    """Форма для специалиста поддержки"""
    categories = forms.ModelMultipleChoiceField(
        queryset=Category.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('Разделы')
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'is_active', 'categories')


class CategoryForm(forms.ModelForm):
    """Форма для раздела"""
    support_users = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_support=True),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label=_('Специалисты поддержки')
    )
    
    class Meta:
        model = Category
        fields = ('name', 'description', 'support_users')


class TicketForm(forms.ModelForm):
    """Форма создания заявки"""
    title = forms.CharField(
        label=_('Тема'),
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите тему заявки'
        })
    )
    description = forms.CharField(
        label=_('Описание'),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Опишите вашу проблему'
        })
    )
    category = forms.ModelChoiceField(
        label=_('Раздел'),
        queryset=Category.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    class Meta:
        model = Ticket
        fields = ('title', 'description', 'category')


class TicketMessageForm(forms.ModelForm):
    """Форма сообщения в заявке"""
    class Meta:
        model = TicketMessage
        fields = ('content',)


class FAQForm(forms.ModelForm):
    """Форма для FAQ"""
    class Meta:
        model = FAQ
        fields = ('category', 'question', 'answer', 'order')
        widgets = {
            'answer': forms.Textarea(attrs={'rows': 6}),
        }


class KnowledgeBaseForm(forms.ModelForm):
    """Форма для базы знаний"""
    class Meta:
        model = KnowledgeBase
        fields = ('title', 'content', 'category')
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
        }