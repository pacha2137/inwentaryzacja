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

    def __str__(self):
        manufacturer = self.manufacturer.strip() if self.manufacturer else 'Brak producenta'
        model = self.model.strip() if self.model else 'Brak modelu'
        return f'{self.tag} — {manufacturer} {model}'


class ChangeHistory(models.Model):
    ACTION_CHOICES = [
        ('create', 'Utworzenie'),
        ('update', 'Edycja'),
        ('delete', 'Usunięcie'),
        ('assign', 'Przypisanie'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='change_history'
    )
    action = models.CharField(max_length=20, choices=ACTION_CHOICES, default='update')
    model_name = models.CharField(max_length=50)
    object_name = models.CharField(max_length=200, blank=True)
    object_id = models.PositiveIntegerField(null=True, blank=True)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.description


class SecurityLog(models.Model):
    """Rejestrowanie zdarzeń bezpieczeństwa"""
    EVENT_TYPES = [
        ('login_success', 'Pomyślne logowanie'),
        ('login_failure', 'Nieudana próba logowania'),
        ('login_locked', 'Konto zablokowane (zbyt wiele prób)'),
        ('permission_change', 'Zmiana uprawnień'),
        ('password_change', 'Zmiana hasła'),
        ('user_created', 'Utworzono użytkownika'),
        ('user_deleted', 'Usunięto użytkownika'),
        ('suspicious_activity', 'Podejrzana aktywność'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_logs'
    )
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['event_type', '-created_at']),
        ]

    def __str__(self):
        return f'{self.get_event_type_display()} - {self.created_at}'
