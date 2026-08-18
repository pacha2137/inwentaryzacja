from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import models
from django.shortcuts import redirect, render
from django.http import HttpResponse, FileResponse
from django.core.cache import cache
from django.views.decorators.http import require_http_methods
import csv
import io
import logging
from pathlib import Path

from .forms import Asset_form, UserPermissionForm, AssignAssetForm, UserCreateForm, UserEditForm, UserPasswordForm, AssetImportForm, UserImportForm, CategoryForm
from .models import Asset, Category, ChangeHistory, SecurityLog

logger = logging.getLogger(__name__)
security_logger = logging.getLogger('django.security')


def serve_style_css(request):
    """Serve the style.css file directly."""
    css_path = Path(__file__).resolve().parent / 'static' / 'assets' / 'css' / 'style.css'
    if css_path.exists():
        return FileResponse(open(css_path, 'rb'), content_type='text/css')
    return HttpResponse("CSS file not found", status=404)


def log_change(request, action, model_name, object_name='', object_id=None, description=None):
    """Create a system change log entry."""
    if description is None:
        description = f'{model_name} "{object_name}"'

    ChangeHistory.objects.create(
        user=request.user if getattr(request, 'user', None) and request.user.is_authenticated else None,
        action=action,
        model_name=model_name,
        object_name=object_name,
        object_id=object_id,
        description=description,
    )


def log_security_event(request, event_type, description, user=None):
    """Log security events for audit trail."""
    ip_address = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')[:500]
    
    SecurityLog.objects.create(
        user=user or (request.user if request.user.is_authenticated else None),
        event_type=event_type,
        ip_address=ip_address,
        user_agent=user_agent,
        description=description,
    )
    
    # Log to security logger as well
    security_logger.warning(f'[{event_type}] {description} - IP: {ip_address}')


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
            log_security_event(request, 'login_locked', f'Wiele nieudanych prób logowania z IP: {ip}')
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
            log_security_event(request, 'login_success', f'Pomyślne logowanie użytkownika: {username}', user)
            return redirect('dashboard')

        # Increment failed attempts
        cache.set(cache_key, attempts + 1, 900)  # 15 minutes = 900 seconds
        logger.warning(f'Failed login attempt for user: {username} from IP: {ip}')
        log_security_event(request, 'login_failure', f'Nieudana próba logowania dla: {username}')
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
        users_count = User.objects.count()
        manufacturers = [
            item['manufacturer']
            for item in assets.exclude(manufacturer='').values('manufacturer').distinct().order_by('manufacturer')
        ]
        all_categories = Category.objects.all().order_by('name')
        recent_assets = assets.order_by('-id')[:5]

        return render(request, 'assets/dashboard_admin.html', {
            'total_assets': total_assets,
            'assigned_assets': assigned_assets,
            'unassigned_assets': unassigned_assets,
            'users_count': users_count,
            'manufacturers': manufacturers,
            'all_categories': all_categories,
            'recent_assets': recent_assets,
        })

    assets = Asset.objects.select_related('category', 'assigned_to').filter(assigned_to=request.user)
    return render(request, 'assets/dashboard_user.html', {
        'assigned_assets': assets,
        'total_assets': assets.count(),
    })


@login_required
def change_history(request):
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')

    entries = ChangeHistory.objects.select_related('user').all()
    return render(request, 'assets/change_history.html', {'entries': entries})


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
    assign_form = None
    assignable_assets = []

    if request.user.is_staff or request.user.is_superuser:
        assignable_assets = Asset.objects.filter(assigned_to__isnull=True).select_related('category', 'assigned_to').order_by('tag')

        if request.method == 'POST':
            if 'assign_asset' in request.POST:
                assign_form = AssignAssetForm(request.POST)
                assign_form.fields['asset'].queryset = assignable_assets
                if assign_form.is_valid():
                    asset = assign_form.cleaned_data['asset']
                    asset.assigned_to = user
                    asset.save(update_fields=['assigned_to'])
                    log_change(
                        request,
                        'assign',
                        'Asset',
                        asset.tag,
                        asset.pk,
                        f'Przypisano sprzęt {asset.tag} do {user.get_full_name() or user.username}.'
                    )
                    messages.success(request, f'Sprzęt {asset.tag} został przypisany do {user.get_full_name() or user.username}.')
                    return redirect('user_detail', id=user.id)
            elif 'remove_asset' in request.POST:
                asset_id = request.POST.get('asset_id')
                if asset_id:
                    asset = Asset.objects.filter(id=asset_id, assigned_to=user).first()
                    if asset:
                        asset.assigned_to = None
                        asset.save(update_fields=['assigned_to'])
                        log_change(
                            request,
                            'update',
                            'Asset',
                            asset.tag,
                            asset.pk,
                            f'Usunięto przypisanie sprzętu {asset.tag} z pracownika {user.get_full_name() or user.username}.'
                        )
                        messages.success(request, f'Przypisanie sprzętu {asset.tag} zostało usunięte.')
                        return redirect('user_detail', id=user.id)

        assign_form = AssignAssetForm()
        assign_form.fields['asset'].queryset = assignable_assets

    return render(request, 'assets/user_detail.html', {
        'user': user,
        'assets': assets,
        'assign_form': assign_form,
        'assignable_assets': assignable_assets,
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
            asset = form.save()
            log_change(
                request,
                'create',
                'Asset',
                asset.tag,
                asset.pk,
                f'Utworzono urządzenie {asset.tag}.'
            )
            messages.success(request, 'Urządzenie zostało dodane.')
            return redirect('asset_list')
    else:
        form = Asset_form()

    return render(request, 'assets/asset_form.html', {
        'form': form,
    })


@login_required
def edit_asset(request, id):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Nie masz uprawnień do edycji urządzeń.')
        return redirect('dashboard')

    asset = Asset.objects.get(id=id)

    if request.method == 'POST':
        form = Asset_form(request.POST, instance=asset)
        if form.is_valid():
            asset = form.save()
            log_change(
                request,
                'update',
                'Asset',
                asset.tag,
                asset.pk,
                f'Edytowano urządzenie {asset.tag}.'
            )
            messages.success(request, 'Urządzenie zostało zaktualizowane.')
            return redirect('asset_detail', id=asset.pk)
    else:
        form = Asset_form(instance=asset)

    return render(request, 'assets/asset_form.html', {
        'form': form,
        'asset': asset,
        'is_edit': True,
    })


@login_required
def delete_asset(request, id):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Nie masz uprawnień do usuwania urządzeń.')
        return redirect('dashboard')

    asset = Asset.objects.get(id=id)

    if request.method == 'POST':
        asset_tag = asset.tag
        log_change(
            request,
            'delete',
            'Asset',
            asset_tag,
            asset.pk,
            f'Usunięto urządzenie {asset_tag}.'
        )
        asset.delete()
        messages.success(request, 'Urządzenie zostało usunięte.')
        return redirect('asset_list')

    return render(request, 'assets/asset_delete_confirm.html', {
        'asset': asset,
    })


@login_required
def category_create(request):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Nie masz uprawnień do zarządzania kategoriami.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            log_change(
                request,
                'create',
                'Category',
                category.name,
                category.pk,
                f'Utworzono kategorię {category.name}.'
            )
            messages.success(request, 'Kategoria została dodana.')
            return redirect('asset_list')
    else:
        form = CategoryForm()

    return render(request, 'assets/category_form.html', {
        'form': form,
    })


@login_required
def category_edit(request, id):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Nie masz uprawnień do zarządzania kategoriami.')
        return redirect('dashboard')

    category = Category.objects.get(id=id)

    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            log_change(
                request,
                'update',
                'Category',
                category.name,
                category.pk,
                f'Edytowano kategorię {category.name}.'
            )
            messages.success(request, 'Kategoria została zaktualizowana.')
            return redirect('asset_list')
    else:
        form = CategoryForm(instance=category)

    return render(request, 'assets/category_form.html', {
        'form': form,
        'category': category,
        'is_edit': True,
    })


@login_required
def category_delete(request, id):
    if not (request.user.is_staff or request.user.is_superuser):
        messages.error(request, 'Nie masz uprawnień do zarządzania kategoriami.')
        return redirect('dashboard')

    category = Category.objects.get(id=id)

    if request.method == 'POST':
        category_name = category.name
        log_change(
            request,
            'delete',
            'Category',
            category_name,
            category.pk,
            f'Usunięto kategorię {category_name}.'
        )
        category.delete()
        messages.success(request, 'Kategoria została usunięta.')
        return redirect('asset_list')

    return render(request, 'assets/category_delete_confirm.html', {
        'category': category,
    })


@login_required
def user_management_list(request):
    """Lista wszystkich pracowników dla admina"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    users = User.objects.all().order_by('username')
    return render(request, 'assets/user_management_list.html', {
        'users': users,
    })


@login_required
def user_create(request):
    """Dodaj nowego pracownika"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.save()
            log_change(
                request,
                'create',
                'Pracownik',
                user.username,
                user.pk,
                f'Utworzono pracownika {user.username}.'
            )
            log_security_event(
                request,
                'user_created',
                f'Utworzono nowego użytkownika: {user.username}',
                user
            )
            messages.success(request, f'Pracownik {user.username} został utworzony.')
            return redirect('user_management_list')
    else:
        form = UserCreateForm()
    
    return render(request, 'assets/user_form.html', {
        'form': form,
        'title': 'Dodaj nowego pracownika',
        'action': 'create',
    })


@login_required
def user_edit(request, id):
    """Edytuj pracownika"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    user = User.objects.get(id=id)
    old_is_staff = user.is_staff
    old_is_superuser = user.is_superuser
    
    if request.method == 'POST':
        form = UserEditForm(request.POST, instance=user)
        password_form = UserPasswordForm(request.POST)
        
        if form.is_valid() and password_form.is_valid():
            form.save()
            
            # Log permission changes
            if old_is_staff != user.is_staff or old_is_superuser != user.is_superuser:
                permission_changes = []
                if old_is_staff != user.is_staff:
                    permission_changes.append(f'is_staff: {old_is_staff} → {user.is_staff}')
                if old_is_superuser != user.is_superuser:
                    permission_changes.append(f'is_superuser: {old_is_superuser} → {user.is_superuser}')
                
                log_security_event(
                    request,
                    'permission_change',
                    f'Zmiana uprawnień użytkownika {user.username}: {", ".join(permission_changes)}',
                    user
                )
            
            # Zmień hasło jeśli zostało podane
            new_password = password_form.cleaned_data.get('password')
            if new_password:
                user.set_password(new_password)
                user.save()
                log_security_event(
                    request,
                    'password_change',
                    f'Zmieniono hasło dla użytkownika {user.username}',
                    user
                )
                messages.success(request, f'Hasło dla {user.username} zostało zmienione.')
            
            log_change(
                request,
                'update',
                'Pracownik',
                user.username,
                user.pk,
                f'Zaktualizowano pracownika {user.username}.'
            )
            messages.success(request, f'Pracownik {user.username} został zaktualizowany.')
            return redirect('user_management_list')
    else:
        form = UserEditForm(instance=user)
        password_form = UserPasswordForm()
    
    return render(request, 'assets/user_edit_form.html', {
        'form': form,
        'password_form': password_form,
        'user_obj': user,
        'title': f'Edytuj pracownika: {user.username}',
    })


@login_required
def user_delete(request, id):
    """Usuń pracownika"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    user = User.objects.get(id=id)
    
    if request.user.id == user.id:
        messages.error(request, 'Nie możesz usunąć siebie samego!')
        return redirect('user_management_list')
    
    if request.method == 'POST':
        username = user.username
        log_change(
            request,
            'delete',
            'Pracownik',
            username,
            user.pk,
            f'Usunięto pracownika {username}.'
        )
        log_security_event(
            request,
            'user_deleted',
            f'Usunięto użytkownika: {username}',
            user
        )
        user.delete()
        messages.success(request, f'Pracownik {username} został usunięty.')
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
                                errors.append(f"Wiersz {row_num}: Pracownik '{row['PRZYPISANO DO']}' nie istnieje")
                                continue
                        
                        serial_number = row.get('NUMER SERYJNY', '').strip()
                        tag = row.get('TAG', '').strip()
                        
                        # If serial_number is empty, use tag as unique identifier
                        if not serial_number:
                            serial_number = tag if tag else None
                        
                        # If both are empty, skip this row
                        if not serial_number:
                            errors.append(f"Wiersz {row_num}: TAG i NUMER SERYJNY są puste")
                            continue
                        
                        # Use update_or_create to handle existing assets with same serial_number
                        asset, created = Asset.objects.update_or_create(
                            serial_number=serial_number,
                            defaults={
                                'tag': tag,
                                'category_id': category,
                                'manufacturer': row.get('PRODUCENT', '').strip(),
                                'model': row.get('MODEL', '').strip(),
                                'assigned_to': assigned_to,
                            }
                        )
                        imported += 1
                    except Exception as e:
                        errors.append(f"Wiersz {row_num}: {str(e)}")
                
                if imported > 0:
                    messages.success(request, f'Zaimportowano {imported} urządzeń.')
                    log_security_event(
                        request,
                        'suspicious_activity',
                        f'Zaimportowano {imported} urządzeń z pliku CSV'
                    )
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
    """Eksportuj pracowników do CSV"""
    if not (request.user.is_staff or request.user.is_superuser):
        return redirect('dashboard')
    
    users = User.objects.all()
    
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="users_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['LOGIN', 'EMAIL', 'IMIĘ', 'NAZWISKO', 'STATUS'])
    
    for user in users:
        status = 'Administrator systemu' if user.is_superuser else ('Administrator' if user.is_staff else 'Pracownik')
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
    """Importuj pracowników z CSV"""
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
                            errors.append(f"Wiersz {row_num}: Pracownik '{row['USERNAME']}' już istnieje")
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
                    messages.success(request, f'Zaimportowano {imported} pracowników.')
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
        