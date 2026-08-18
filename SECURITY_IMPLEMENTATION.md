# Zabezpieczenia - Inwentaryzacja

## Co zostało zrobione

### Rate Limiting
Dodane django-axes, max 5 nieudanych prób zalogowania → blokada na 30 minut. Konfiguracja w settings.py.

```python
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_DURATION = 30  # minutes
```

### Security Logging
Model `SecurityLog` śledzi wszystkie ważne zdarzenia: logowania, zmiany uprawnień, usunięcia użytkowników. Każde zdarzenie z IP i User-Agent. Widoczne w panelu admina (`/admin/`).

Logowane akcje:
- Logowanie (sukces/porażka)
- Zmiana uprawnień (is_staff, is_superuser)
- Zmiana hasła
- Utworzenie/usunięcie użytkownika

### Bezpieczne sesje
Cookies z flagami HttpOnly, SameSite=Strict. HSTS włączony, ochrona przed clickjacking (X-Frame-Options: DENY).

```python
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = 'Strict'
```

### Historia zmian
Wszystkie operacje na danych logowane - kto, co, kiedy. Widoczne w zakładce "Historia zmian".


## Pliki

- `inwentaryzacja/settings.py` - konfiguracja axes i security headers
- `assets/models.py` - model SecurityLog
- `assets/views.py` - logowanie zdarzeń w login_view, user_create, user_edit, user_delete
- `assets/admin.py` - admin interface dla logów (read-only)
