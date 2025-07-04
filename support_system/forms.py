from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import User, Ticket, TicketMessage, Category, Content, FAQ, KnowledgeBase, SupportRating
from django.core.exceptions import ValidationError


class UserRegistrationForm(UserCreationForm):
    # Форма регистрации пользователя
    email = forms.EmailField(
        label=_('Адрес электронной почты'),
        widget=forms.TextInput(attrs={'autocomplete': 'email'}),
        error_messages={
            'invalid': _('Введите корректный адрес электронной почты.'),
            'required': _('Пожалуйста, укажите адрес электронной почты.'),
        }
    )
    username = forms.CharField(
        label=_('Имя пользователя'),
        error_messages={
            'required': _('Пожалуйста, укажите имя пользователя.'),
            'unique': _('Пользователь с таким именем уже существует.'),
        }
    )
    password1 = forms.CharField(
        label=_('Пароль'),
        widget=forms.PasswordInput,
        error_messages={
            'required': _('Пожалуйста, введите пароль.'),
        }
    )
    password2 = forms.CharField(
        label=_('Подтверждение пароля'),
        widget=forms.PasswordInput,
        error_messages={
            'required': _('Пожалуйста, повторите пароль.'),
        }
    )
    first_name = forms.CharField(
        label=_('Имя'),
        error_messages={
            'required': _('Пожалуйста, укажите имя.'),
        }
    )
    last_name = forms.CharField(
        label=_('Фамилия'),
        error_messages={
            'required': _('Пожалуйста, укажите фамилию.'),
        }
    )
    phone = forms.CharField(
        label=_('Телефон'),
        error_messages={
            'invalid': _('Введите корректный номер телефона.'),
            'required': _('Пожалуйста, укажите номер телефона.'),
        },
        widget=forms.TextInput(attrs={'pattern': r'^[+]?\d{10,15}$', 'title': 'Только цифры, можно начинать с +', 'inputmode': 'tel'})
    )
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2:
            if password1 != password2:
                raise ValidationError(_('Введённые пароли не совпадают.'))
            if len(password1) < 8:
                raise ValidationError(_('Пароль слишком короткий. Минимум 8 символов.'))
        return password2
    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        print('DEBUG phone:', repr(phone))
        import re
        if phone:
            if not re.fullmatch(r'^[+]?[0-9]{10,15}$', phone):
                raise ValidationError(_('Введите корректный номер телефона (только цифры, 10-15 символов, можно начинать с +).'))
            digits = phone[1:] if phone.startswith('+') else phone
            if not (10 <= len(digits) <= 15):
                raise ValidationError(_('Длина номера телефона должна быть от 10 до 15 цифр.'))
        return phone
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2', 'first_name', 'last_name', 'phone')
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].validators = [v for v in self.fields['password1'].validators if v.__class__.__name__ == 'MinimumLengthValidator']

    def save(self, commit=True):
        self.full_clean()
        return super().save(commit=commit)


class UserLoginForm(forms.Form):
    # Форма входа
    username = forms.CharField(label='Имя пользователя')
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput)


class UserForm(forms.ModelForm):
    # Форма для пользователя
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone', 'is_active')


class SupportUserForm(forms.ModelForm):
    # Форма для специалиста поддержки
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
        }),
        empty_label=None
    )
    
    class Meta:
        model = Ticket
        fields = ('title', 'description', 'category')


class TicketMessageForm(forms.ModelForm):
    """Форма сообщения в заявке"""
    content = forms.CharField(required=False, widget=forms.Textarea, label=_('Текст сообщения'))
    class Meta:
        model = TicketMessage
        fields = ('content',)


class ContentForm(forms.ModelForm):
    """Форма для контента (FAQ и База знаний)"""
    class Meta:
        model = Content
        fields = ('type', 'category', 'title', 'content', 'order')
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
        }


class FAQForm(forms.ModelForm):
    class Meta:
        model = FAQ
        fields = ['category', 'question', 'answer', 'order']
        widgets = {
            'answer': forms.Textarea(attrs={'rows': 4}),
        }


class KnowledgeBaseForm(forms.ModelForm):
    class Meta:
        model = KnowledgeBase
        fields = ['title', 'content', 'category']
        widgets = {
            'content': forms.Textarea(attrs={'rows': 10}),
        }


class SupportRatingForm(forms.ModelForm):
    score = forms.ChoiceField(
        choices=[(i, f'{i} звёзд') for i in range(1, 6)],
        widget=forms.RadioSelect,
        label='Оценка'
    )
    class Meta:
        model = SupportRating
        fields = ['score', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 2, 'placeholder': 'Комментарий (необязательно)'}),
        }


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }