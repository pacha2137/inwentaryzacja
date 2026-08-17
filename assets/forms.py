from django import forms
from django.contrib.auth.models import Group, User
from .models import Asset, Category


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']
        labels = {
            'name': 'Nazwa kategorii',
        }

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if Category.objects.filter(name__iexact=name).exists():
            raise forms.ValidationError('Kategoria o tej nazwie już istnieje.')
        return name


class Asset_form(forms.ModelForm):
    class Meta:
        model = Asset
        fields = [
            'tag',
            'category',
            'manufacturer',
            'model',
            'serial_number',
            'assigned_to',
        ]


class UserPermissionForm(forms.Form):
    user = forms.ModelChoiceField(queryset=User.objects.none(), label='Użytkownik')
    is_staff = forms.BooleanField(required=False, label='Czy ma dostęp administratora')
    is_superuser = forms.BooleanField(required=False, label='Czy ma pełne uprawnienia')
    groups = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label='Role / grupy',
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.order_by('username')


class UserCreateForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label='Hasło',
        help_text='Wprowadź hasło dla nowego użytkownika'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label='Potwierdź hasło',
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        labels = {
            'username': 'Login',
            'email': 'Email',
            'first_name': 'Imię',
            'last_name': 'Nazwisko',
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError('Hasła nie są identyczne.')
        
        return cleaned_data


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']
        labels = {
            'email': 'Email',
            'first_name': 'Imię',
            'last_name': 'Nazwisko',
        }


class UserPasswordForm(forms.Form):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label='Nowe hasło',
        required=False,
        help_text='Jeśli zostawisz puste, hasło nie zmieni się'
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput,
        label='Potwierdź hasło',
        required=False,
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        
        if password or password_confirm:
            if password != password_confirm:
                raise forms.ValidationError('Hasła nie są identyczne.')
        
        return cleaned_data


class AssetImportForm(forms.Form):
    csv_file = forms.FileField(
        label='Plik CSV',
        help_text='Plik musi zawierać kolumny: tag, category, manufacturer, model, serial_number, assigned_to (login)',
        widget=forms.FileInput(attrs={'accept': '.csv'})
    )
    
    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        if not file.name.endswith('.csv'):
            raise forms.ValidationError('Plik musi mieć rozszerzenie .csv')
        return file


class UserImportForm(forms.Form):
    csv_file = forms.FileField(
        label='Plik CSV',
        help_text='Plik musi zawierać kolumny: username, email, first_name, last_name, password',
        widget=forms.FileInput(attrs={'accept': '.csv'})
    )
    
    def clean_csv_file(self):
        file = self.cleaned_data['csv_file']
        if not file.name.endswith('.csv'):
            raise forms.ValidationError('Plik musi mieć rozszerzenie .csv')
        return file

