"""
Error handling views for custom error pages
"""

from django.shortcuts import render
from django.views.decorators.http import require_http_methods
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def error_404(request, exception=None):
    """Handle 404 Not Found errors."""
    logger.warning(f'404 error on path: {request.path}')
    return render(request, 'assets/error_404.html', status=404)


@require_http_methods(["GET"])
def error_500(request):
    """Handle 500 Internal Server errors."""
    logger.error(f'500 error on path: {request.path}')
    return render(request, 'assets/error_500.html', status=500)


@require_http_methods(["GET"])
def error_403(request, reason=''):
    """Handle 403 Forbidden errors."""
    logger.warning(f'403 error on path: {request.path}. Reason: {reason}')
    return render(request, 'assets/error_403.html', status=403)
