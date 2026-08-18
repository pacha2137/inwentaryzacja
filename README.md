# Inwentaryzacja

Zaawansowana aplikacja do zarządzania inwentaryzacją sprzętu i pracownikami.

## Funkcje

### Zarządzanie urządzeniami
- Lista urządzeń z wyszukiwaniem po identyfikatorze, numerze seryjnym, producencie, modelu i pracowniku
- Dodawanie, edytowanie i usuwanie urządzeń
- Przypisywanie urządzeń do pracowników
- Import/eksport urządzeń z/do CSV
- Szczegółowy widok urządzenia

### Zarządzanie pracownikami (admin)
- Lista wszystkich pracowników
- Dodawanie, edytowanie i usuwanie pracowników
- Zarządzanie uprawnieniami (administrator, pełne uprawnienia)
- Edycja haseł
- Przypisywanie urządzeń do pracowników

### Zarządzanie kategoriami
- Dodawanie, edytowanie i usuwanie rodzajów urządzeń
- Widok wszystkich rodzajów na dashboardzie

### Historia zmian i audyt
- Pełna historia wszystkich zmian w systemie
- Logowanie akcji: utworzenie, edycja, usunięcie, przypisanie, usunięcie przypisania
- Wyświetlanie użytkownika wykonującego zmianę i czasu
- **Logi bezpieczeństwa**: Logowanie logowań, zmian uprawnień, usunięć użytkowników i próby nieautoryzowanego dostępu
- Dostęp do logów w panelu administratora

### Dashboard
- Statystyka: liczba wszystkich urządzeń, przypisanych, wolnych i pracowników
- Lista producentów sprzętu
- Ostatnio dodane urządzenia
- Rodzaje urządzeń z możliwością edycji i usunięcia

### Bezpieczeństwo
- System uwierzytelniania Django
- Podziały uprawnień (administrator systemu, administrator, pracownik)
- Ochrona przed nieautoryzowanym dostępem do funkcji admin
- Interfejs w pełni po polsku
- **Rate limiting (django-axes)**: Maksymalnie 5 nieudanych prób logowania; blokada na 30 minut
- **Audyt bezpieczeństwa**: Logowanie wszystkich logowań, zmian uprawnień, usunięć użytkowników
- **CSRF Protection**: Automatyczna ochrona przed atakami CSRF
- **Secure cookies**: HttpOnly, Secure, SameSite flagi
- **Security headers**: HSTS, X-Frame-Options, Content-Security-Policy

## Tech stack

- Python 3.11+
- Django 5.2.4
- SQLite database
- Bootstrap 5 (responsive design)

## Project structure

- `inwentaryzacja/` – Django project configuration
- `assets/` – inventory application logic, templates, and static files
- `db.sqlite3` – local development database

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. Install dependencies:

   ```bash
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

3. Apply database migrations:

   ```bash
   python manage.py migrate
   ```

4. Create a default admin account:

   ```bash
   python manage.py seed_admin
   ```

   Default credentials:
   - Username: `admin`
   - Password: `admin123`

5. Run the app:

   ```bash
   python manage.py runserver
   ```

6. Otwórz aplikację w przeglądarce:
   - Strona logowania: `http://127.0.0.1:8000/`
   - Panel administratora: `http://127.0.0.1:8000/dashboard/`
   - Lista urządzeń: `http://127.0.0.1:8000/assets/`

## Domyślny login

Użyj konta administratora do dostępu do aplikacji:

- Konto: `admin`
- Hasło: `admin123`

## Struktura interfejsu

### Dla administratorów
- **Przegląd** – Dashboard ze statystyką i najnowszymi zmianami
- **Urządzenia** – Zarządzanie sprzętem (dodawanie, edytowanie, usuwanie, import/eksport)
- **Zarządzanie** – Zarządzanie pracownikami i ich uprawnieniami
- **Historia zmian** – Pełny audyt wszystkich zmian w systemie

### Dla zwykłych pracowników
- **Przegląd** – Widok przeglądu
- **Urządzenia** – Lista dostępnego sprzętu
- **Pracownicy** – Lista pracowników (widoczna tylko dla adminów)

## Planowane funkcje

- Synchronizacja z Active Directory (AD)
- Powiadomienia e-mail
- Raporty zaawansowane
