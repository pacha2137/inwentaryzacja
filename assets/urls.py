from django.urls import path
from . import views


urlpatterns = [
    path('', views.asset_list, name='asset_list'),
    path('<int:id>/', views.asset_detail, name='asset_detail'),
    path('users/', views.user_list, name='user_list'),
    path('users/<int:id>/', views.user_detail, name='user_detail'),
    path('create/', views.add_asset, name='asset_create'),
]