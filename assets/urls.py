from django.contrib.auth.decorators import login_required
from django.urls import path, re_path
from . import views
from .views_error import error_404


urlpatterns = [
    path('static/assets/css/style.css', views.serve_style_css, name='serve_style_css'),
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', login_required(views.dashboard, login_url='login'), name='dashboard'),
    path('history/', login_required(views.change_history, login_url='login'), name='change_history'),
    path('assets/', login_required(views.asset_list, login_url='login'), name='asset_list'),
    path('assets/create/', login_required(views.add_asset, login_url='login'), name='asset_create'),
    path('assets/<int:id>/edit/', login_required(views.edit_asset, login_url='login'), name='edit_asset'),
    path('assets/<int:id>/delete/', login_required(views.delete_asset, login_url='login'), name='delete_asset'),
    path('assets/<int:id>/', login_required(views.asset_detail, login_url='login'), name='asset_detail'),
    path('users/', login_required(views.user_list, login_url='login'), name='user_list'),
    path('users/<int:id>/', login_required(views.user_detail, login_url='login'), name='user_detail'),
    path('categories/create/', login_required(views.category_create, login_url='login'), name='category_create'),
    path('categories/<int:id>/edit/', login_required(views.category_edit, login_url='login'), name='category_edit'),
    path('categories/<int:id>/delete/', login_required(views.category_delete, login_url='login'), name='category_delete'),
    path('permissions/', login_required(views.permissions_panel, login_url='login'), name='permissions_panel'),
    path('management/users/', login_required(views.user_management_list, login_url='login'), name='user_management_list'),
    path('management/users/create/', login_required(views.user_create, login_url='login'), name='user_create'),
    path('management/users/<int:id>/edit/', login_required(views.user_edit, login_url='login'), name='user_edit'),
    path('management/users/<int:id>/delete/', login_required(views.user_delete, login_url='login'), name='user_delete'),
    path('export/assets/', login_required(views.export_assets_csv, login_url='login'), name='export_assets'),
    path('import/assets/', login_required(views.import_assets_csv, login_url='login'), name='import_assets'),
    path('export/users/', login_required(views.export_users_csv, login_url='login'), name='export_users'),
    path('import/users/', login_required(views.import_users_csv, login_url='login'), name='import_users'),
    
    # Catch-all pattern for 404 errors (must be last)
    re_path(r'^.*$', error_404, name='catch_all_404'),
]