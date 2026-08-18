from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from .models import Asset, Category, ChangeHistory


class InventoryAuthTests(TestCase):
    def setUp(self):
        self.admin = get_user_model().objects.create_user(
            username='admin',
            email='admin@example.com',
            password='StrongPass123',
            first_name='Admin',
            last_name='User'
        )
        self.admin.is_staff = True
        self.admin.save()

        self.user = get_user_model().objects.create_user(
            username='regular',
            email='regular@example.com',
            password='UserPass123',
            first_name='Regular',
            last_name='User'
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Zaloguj się')

    def test_assets_require_login(self):
        response = self.client.get(reverse('asset_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('next=/assets/', response.url)

    def test_user_can_login_and_access_assets(self):
        login_response = self.client.login(username='admin', password='StrongPass123')
        self.assertTrue(login_response)
        response = self.client.get(reverse('asset_list'))
        self.assertEqual(response.status_code, 200)

    def test_regular_user_cannot_access_asset_create(self):
        self.client.login(username='regular', password='UserPass123')
        response = self.client.get(reverse('asset_create'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))

    def test_admin_can_access_category_create(self):
        self.client.login(username='admin', password='StrongPass123')
        response = self.client.get(reverse('category_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nowy rodzaj')

    def test_admin_can_assign_asset_to_user(self):
        self.client.login(username='admin', password='StrongPass123')
        category = Category.objects.create(name='Testowa kategoria')
        asset = Asset.objects.create(
            tag='ASSIGN-001',
            serial_number='SN-ASSIGN-001',
            category=category,
            manufacturer='Dell',
            model='Latitude 7400'
        )

        response = self.client.post(
            reverse('user_detail', args=[self.user.pk]),
            {'assign_asset': '1', 'asset': str(asset.pk)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        asset.refresh_from_db()
        self.assertEqual(asset.assigned_to_id, self.user.pk)
        self.assertContains(response, 'Przypisz urządzenie')
        self.assertTrue(ChangeHistory.objects.filter(action='assign', model_name='Asset').exists())

    def test_admin_can_remove_asset_assignment_from_user(self):
        self.client.login(username='admin', password='StrongPass123')
        category = Category.objects.create(name='Testowa kategoria 2')
        asset = Asset.objects.create(
            tag='ASSIGN-REMOVE-001',
            serial_number='SN-REMOVE-001',
            category=category,
            manufacturer='HP',
            model='EliteBook'
        )
        asset.assigned_to = self.user
        asset.save(update_fields=['assigned_to'])

        response = self.client.post(
            reverse('user_detail', args=[self.user.pk]),
            {'remove_asset': '1', 'asset_id': str(asset.pk)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        asset.refresh_from_db()
        self.assertIsNone(asset.assigned_to)
        self.assertContains(response, 'Przypisanie sprzętu')

    def test_admin_can_access_change_history_page(self):
        self.client.login(username='admin', password='StrongPass123')
        response = self.client.get(reverse('change_history'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Historia zmian')

    def test_invalid_url_returns_custom_404_page(self):
        response = self.client.get('/this-url-does-not-exist-123/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Strona nie znaleziona', status_code=404)
