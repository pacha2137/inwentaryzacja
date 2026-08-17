from django.contrib.auth.decorators import login_required
from django.urls import path
from . import views


urlpatterns = [
    path('', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', login_required(views.dashboard, login_url='login'), name='dashboard'),
    path('assets/', login_required(views.asset_list, login_url='login'), name='asset_list'),
    path('assets/<int:id>/', login_required(views.asset_detail, login_url='login'), name='asset_detail'),
    path('users/', login_required(views.user_list, login_url='login'), name='user_list'),
    path('users/<int:id>/', login_required(views.user_detail, login_url='login'), name='user_detail'),
    path('assets/create/', login_required(views.add_asset, login_url='login'), name='asset_create'),
    path('categories/create/', login_required(views.category_create, login_url='login'), name='category_create'),
    path('permissions/', login_required(views.permissions_panel, login_url='login'), name='permissions_panel'),
    path('management/users/', login_required(views.user_management_list, login_url='login'), name='user_management_list'),
    path('management/users/create/', login_required(views.user_create, login_url='login'), name='user_create'),
    path('management/users/<int:id>/edit/', login_required(views.user_edit, login_url='login'), name='user_edit'),
    path('management/users/<int:id>/delete/', login_required(views.user_delete, login_url='login'), name='user_delete'),
    path('export/assets/', login_required(views.export_assets_csv, login_url='login'), name='export_assets'),
    path('import/assets/', login_required(views.import_assets_csv, login_url='login'), name='import_assets'),
    path('export/users/', login_required(views.export_users_csv, login_url='login'), name='export_users'),
    path('import/users/', login_required(views.import_users_csv, login_url='login'), name='import_users'),
]