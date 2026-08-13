from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Asset(models.Model):
    tag = models.CharField(max_length=30, unique=True)
    serial_number = models.CharField(max_length=30, blank = True, unique=True)
    manufacturer = models.CharField(max_length=30, blank = True)
    model = models.CharField(max_length=30, blank = True)

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='assets'
    )

    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null = True,
        blank = True,
        related_name='assets'
    )


