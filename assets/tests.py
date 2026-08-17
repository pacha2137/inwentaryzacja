from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model


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
        self.assertContains(response, 'Dodaj kategorię')

    def test_invalid_url_returns_custom_404_page(self):
        response = self.client.get('/this-url-does-not-exist-123/')
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, 'Strona nie znaleziona', status_code=404)
