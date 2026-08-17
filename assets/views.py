from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import models
from django.shortcuts import redirect, render
from django.http import HttpResponse
from django.core.cache import cache
from django.views.decorators.http import require_http_methods
import csv
import io
import logging

from .forms import Asset_form, UserPermissionForm, UserCreateForm, UserEditForm, UserPasswordForm, AssetImportForm, UserImportForm, CategoryForm
from .models import Asset, Category

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Get client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def login_view(request):
    """Handle user login with rate limiting."""
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        # Rate limiting: 5 attempts per 15 minutes
        ip = get_client_ip(request)
        cache_key = f'login_attempts_{ip}'
        attempts = cache.get(cache_key, 0)

        if attempts >= 5:
            logger.warning(f'Blocked login attempts from IP: {ip} (attempt {attempts + 1})')
            messages.error(request, 'Zbyt wiele nieudanych prób. Spróbuj za 15 minut.')
            return render(request, 'assets/login_panel.html')

        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
        # Validate input
        if not username or not password:
            messages.error(request, 'Wpisz login i hasło.')
            return render(request, 'assets/login_panel.html')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            # Reset attempts on successful login
            cache.delete(cache_key)
            login(request, user)
            logger.info(f'Successful login for user: {username}')
            return redirect('dashboard')

        # Increment failed attempts
        cache.set(cache_key, attempts + 1, 900)  # 15 minutes = 900 seconds
        logger.warning(f'Failed login attempt for user: {username} from IP: {ip}')
        messages.error(request, 'Nieprawidłowy login lub hasło.')

    return render(request, 'assets/login_panel.html')


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def dashboard(request):
    if request.user.is_superuser or request.user.is_staff:
        assets = Asset.objects.select_related('category', 'assigned_to').all()
        total_assets = assets.count()
        assigned_assets = assets.filter(assigned_to__isnull=False).count()
        unassigned_assets = total_assets - assigned_assets
        categories_count = assets.values_list('category_id', flat=True).distinct().count()
        manufacturers = [
            item['manufacturer']
            for item in assets.exclude(manufacturer='').values('manufacturer').distinct().order_by('manufacturer')
        ]
        recent_assets = assets.order_by('-id')[:5]

        return render(request, 'assets/dashboard_admin.html', {
            'total_assets': total_assets,
            'assigned_assets': assigned_assets,
            'unassigned_assets': unassigned_assets,
            'categories_count': categories_count,
            'manufacturers': manufacturers,
            'recent_assets': recent_assets,
        })

    assets = Asset.objects.select_related('category', 'assigned_to').filter(assigned_to=request.user)
    return render(request, 'assets/dashboard_user.html', {
        'assigned_assets': assets,
        'total_assets': assets.count(),
    })


@login_required
def permissions_panel(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')

    form = UserPermissionForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        selected_user = form.cleaned_data['user']
        selected_user.is_staff = form.cleaned_data['is_staff']
        selected_user.is_superuser = form.cleaned_data['is_superuser']
        selected_user.groups.set(form.cleaned_data['groups'])
        selected_user.save()
        messages.success(request, f'Uprawnienia zostały zaktualizowane dla {selected_user.username}.')
        return redirect('permissions_panel')

    return render(request, 'assets/permissions_panel.html', {'form': form})


def asset_list(request):
    query = request.GET.get('q', '')
    selected_mark = request.GET.get('mark', '').strip()

    assets = Asset.objects.select_related(
        'category',
        'assigned_to'
    ).all()

    if selected_mark:
        assets = assets.filter(manufacturer__icontains=selected_mark)

    if query:
        assets = assets.filter(
            models.Q(tag__icontains=query) |
            models.Q(serial_number__icontains=query) |
            models.Q(manufacturer__icontains=query) |
            models.Q(model__icontains=query) |
            models.Q(category__name__icontains=query) |
            models.Q(assigned_to__username__icontains=query) |
            models.Q(assigned_to__first_name__icontains=query) |
            models.Q(assigned_to__last_name__icontains=query)
        )

    brands = Asset.objects.exclude(manufacturer='').values_list('manufacturer', flat=True).distinct().order_by('manufacturer')

    return render(request, 'assets/asset_list.html', {
        'assets': assets,
        'query': query,
        'selected_mark': selected_mark,
        'brands': brands,
    })


def asset_detail(request, id):
    asset = Asset.objects.get(id=id)

    return render(request, 'assets/asset_detail.html', {
        'asset': asset
    })


def user_detail(request, id):
    user = User.objects.get(id=id)
    assets = user.assets.select_related('category').all()

    return render(request, 'assets/user_detail.html', {
        'user': user,
        'assets': assets,
    })

def user_list(request):
    users = User.objects.all()

    return render(request, 'assets/user_list.html', {
        'users' : users,
    })

@login_required
def add_asset(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Nie masz uprawnień do dodawania urządzeń.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = Asset_form(request.POST)

        if form.is_valid():
            form.save()
            messages.success(request, 'Urządzenie zostało dodane.')
            return redirect('asset_list')
    else:
        form = Asset_form()

    return render(request, 'assets/asset_form.html', {
        'form': form,
    })


@login_required
def category_create(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Nie masz uprawnień do zarządzania kategoriami.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Kategoria została dodana.')
            return redirect('asset_list')
    else:
        form = CategoryForm()

    return render(request, 'assets/category_form.html', {
        'form': form,
    })


@login_required
def user_management_list(request):
    """Lista wszystkich użytkowników dla admina"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    users = User.objects.all().order_by('username')
    return render(request, 'assets/user_management_list.html', {
        'users': users,
    })


@login_required
def user_create(request):
    """Dodaj nowego użytkownika"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, f'Użytkownik {user.username} został utworzony.')
            return redirect('user_management_list')
    else:
        form = UserCreateForm()
    
    return render(request, 'assets/user_form.html', {
        'form': form,
        'title': 'Dodaj nowego użytkownika',
        'action': 'create',
    })


@login_required
def user_edit(request, id):
    """Edytuj użytkownika"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    user = User.objects.get(id=id)
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        password_form = UserPasswordForm(request.POST)
        
        if form.is_valid() and password_form.is_valid():
            form.save()
            
            # Zmień hasło jeśli zostało podane
            new_password = password_form.cleaned_data.get('password')
            if new_password:
                user.set_password(new_password)
                user.save()
                messages.success(request, f'Hasło dla {user.username} zostało zmienione.')
            
            messages.success(request, f'Użytkownik {user.username} został zaktualizowany.')
            return redirect('user_management_list')
    else:
        form = UserEditForm(instance=user)
        password_form = UserPasswordForm()
    
    return render(request, 'assets/user_edit_form.html', {
        'form': form,
        'password_form': password_form,
        'user_obj': user,
        'title': f'Edytuj użytkownika: {user.username}',
    })


@login_required
def user_delete(request, id):
    """Usuń użytkownika"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    user = User.objects.get(id=id)
    
    if request.user.id == user.id:
        messages.error(request, 'Nie możesz usunąć siebie samego!')
        return redirect('user_management_list')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Użytkownik {username} został usunięty.')
        return redirect('user_management_list')
    
    return render(request, 'assets/user_delete_confirm.html', {
        'user_obj': user,
    })


@login_required
def export_assets_csv(request):
    """Eksportuj urządzenia do CSV"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    assets = Asset.objects.select_related('category', 'assigned_to').all()
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="assets_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['TAG', 'KATEGORIA', 'PRODUCENT', 'MODEL', 'NUMER SERYJNY', 'PRZYPISANO DO'])
    
    for asset in assets:
        writer.writerow([
            asset.tag,
            asset.category.name if asset.category else '',
            asset.manufacturer,
            asset.model,
            asset.serial_number,
            asset.assigned_to.username if asset.assigned_to else '',
        ])
    
    return response


@login_required
def import_assets_csv(request):
    """Importuj urządzenia z CSV"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = AssetImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            # Validate file size (max 5MB)
            if csv_file.size > 5242880:
                messages.error(request, 'Plik jest zbyt duży. Maksymalny rozmiar to 5MB.')
                return render(request, 'assets/import_assets.html', {'form': form})
            
            # Validate file extension
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Plik musi mieć rozszerzenie .csv')
                return render(request, 'assets/import_assets.html', {'form': form})
            
            stream = io.TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.DictReader(stream)
            
            imported = 0
            errors = []
            
            try:
                for row_num, row in enumerate(reader, start=2):
                    try:
                        category = None
                        if row.get('KATEGORIA'):
                            category = Asset.objects.values_list('category', flat=True).first()
                        
                        assigned_to = None
                        if row.get('PRZYPISANO DO'):
                            try:
                                assigned_to = User.objects.get(username=row['PRZYPISANO DO'])
                            except User.DoesNotExist:
                                errors.append(f"Wiersz {row_num}: Użytkownik '{row['PRZYPISANO DO']}' nie istnieje")
                                continue
                        
                        Asset.objects.create(
                            tag=row.get('TAG', ''),
                            category_id=category,
                            manufacturer=row.get('PRODUCENT', ''),
                            model=row.get('MODEL', ''),
                            serial_number=row.get('NUMER SERYJNY', ''),
                            assigned_to=assigned_to,
                        )
                        imported += 1
                    except Exception as e:
                        errors.append(f"Wiersz {row_num}: {str(e)}")
                
                if imported > 0:
                    messages.success(request, f'Zaimportowano {imported} urządzeń.')
                if errors:
                    for error in errors:
                        messages.warning(request, error)
                
                logger.info(f'CSV import: {imported} assets imported by user {request.user.username}')
                return redirect('asset_list')
            except Exception as e:
                logger.error(f'CSV import error: {str(e)}')
                messages.error(request, f'Błąd podczas importu: {str(e)}')
    else:
        form = AssetImportForm()
    
    return render(request, 'assets/import_assets.html', {'form': form})


@login_required
def export_users_csv(request):
    """Eksportuj użytkowników do CSV"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    users = User.objects.all()
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="users_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['LOGIN', 'EMAIL', 'IMIĘ', 'NAZWISKO', 'STATUS'])
    
    for user in users:
        status = 'Superuser' if user.is_superuser else ('Admin' if user.is_staff else 'Użytkownik')
        writer.writerow([
            user.username,
            user.email,
            user.first_name,
            user.last_name,
            status,
        ])
    
    return response


@login_required
def import_users_csv(request):
    """Importuj użytkowników z CSV"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserImportForm(request.POST, request.FILES)
        if form.is_valid():
            csv_file = request.FILES['csv_file']
            
            # Validate file size (max 5MB)
            if csv_file.size > 5242880:
                messages.error(request, 'Plik jest zbyt duży. Maksymalny rozmiar to 5MB.')
                return render(request, 'assets/import_users.html', {'form': form})
            
            # Validate file extension
            if not csv_file.name.endswith('.csv'):
                messages.error(request, 'Plik musi mieć rozszerzenie .csv')
                return render(request, 'assets/import_users.html', {'form': form})
            
            stream = io.TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.DictReader(stream)
            
            imported = 0
            errors = []
            
            try:
                for row_num, row in enumerate(reader, start=2):
                    try:
                        if not row.get('USERNAME'):
                            errors.append(f"Wiersz {row_num}: USERNAME jest wymagany")
                            continue
                        
                        if User.objects.filter(username=row['USERNAME']).exists():
                            errors.append(f"Wiersz {row_num}: Użytkownik '{row['USERNAME']}' już istnieje")
                            continue
                        
                        user = User.objects.create_user(
                            username=row.get('USERNAME', ''),
                            email=row.get('EMAIL', ''),
                            first_name=row.get('FIRST_NAME', ''),
                            last_name=row.get('LAST_NAME', ''),
                            password=row.get('PASSWORD', 'DefaultPass123!')
                        )
                        imported += 1
                    except Exception as e:
                        errors.append(f"Wiersz {row_num}: {str(e)}")
                
                if imported > 0:
                    messages.success(request, f'Zaimportowano {imported} użytkowników.')
                if errors:
                    for error in errors:
                        messages.warning(request, error)
                
                logger.info(f'CSV user import: {imported} users imported by {request.user.username}')
                return redirect('user_management_list')
            except Exception as e:
                logger.error(f'CSV user import error: {str(e)}')
                messages.error(request, f'Błąd podczas importu: {str(e)}')
    else:
        form = UserImportForm()
    
    return render(request, 'assets/import_users.html', {'form': form})
        