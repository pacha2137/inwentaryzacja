"""
Custom middleware for security features:
- Rate limiting for brute force protection
- Custom error handling
- Security headers
"""

from django.core.cache import cache
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)


class RateLimitMiddleware(MiddlewareMixin):
    """Rate limiting to prevent brute force attacks."""

    def __init__(self, get_response):
        self.get_response = get_response
        super().__init__(get_response)

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Rate limit only login attempts
        if request.path == '/' and request.method == 'POST':
            return self.check_rate_limit(request)
        return None

    def check_rate_limit(self, request):
        """Check if IP exceeded rate limit for login attempts."""
        ip = self.get_client_ip(request)
        cache_key = f'login_attempts_{ip}'
        attempts = cache.get(cache_key, 0)

        if attempts >= 5:
            logger.warning(f'Blocked multiple login attempts from IP: {ip}')
            return JsonResponse(
                {'error': 'Zbyt wiele nieudanych prób logowania. Spróbuj za 15 minut.'},
                status=429
            )

        return None

    def get_client_ip(self, request):
        """Get client IP from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def process_response(self, request, response):
        """Add security headers to response."""
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
        
        return response


class CustomErrorHandlerMiddleware(MiddlewareMixin):
    """Handle 404 and 500 errors without exposing internal details."""

    def process_exception(self, request, exception):
        """Log exceptions and return generic error message."""
        logger.error(f'Exception on {request.path}: {str(exception)}', exc_info=True)
        
        if request.headers.get('Accept') == 'application/json':
            return JsonResponse(
                {'error': 'Wewnętrzny błąd serwera'},
                status=500
            )
        return None  # Let Django handle it


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add security headers to all responses."""

    def process_response(self, request, response):
        """Add CSP and other security headers."""
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        
        return response
