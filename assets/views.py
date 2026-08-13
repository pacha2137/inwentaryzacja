from django.shortcuts import redirect, render
from .models import Asset
from django.contrib.auth.models import User
from django.db import models
from .forms import Asset_form


def asset_list(request):
    query = request.GET.get('q', '')

    assets = Asset.objects.select_related(
        'category',
        'assigned_to'
    ).all()

    if query:
        assets=assets.filter(
            models.Q(tag__icontains=query) |
            models.Q(serial_number__icontains=query) |
            models.Q(manufacturer__icontains=query) |
            models.Q(model__icontains=query) |
            models.Q(category__name__icontains=query) |
            models.Q(assigned_to__username__icontains=query) |
            models.Q(assigned_to__first_name__icontains=query) |
            models.Q(assigned_to__last_name__icontains=query) 
        )

    return render(request, 'assets/asset_list.html', {
        'assets': assets,
        'query' : query,
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

def add_asset(request):
    if request.method == 'POST':
        form = Asset_form(request.POST)

        if form.is_valid():
            form.save()
            return redirect('asset_list')
        
    else:
        form = Asset_form()
        
    return render(request,'assets/asset_form.html', {
        'form': form,
    })
        