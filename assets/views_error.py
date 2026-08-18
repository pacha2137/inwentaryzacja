"""Custom Django error handlers."""

import logging

from django.shortcuts import render
from django.views.decorators.http import require_http_methods

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def error_404(request, exception=None):
    """Render custom 404 page."""
    logger.warning("404 error on path: %s", request.path)
    return render(request, '404.html', status=404)


@require_http_methods(["GET"])
def error_500(request):
    """Render custom 500 page."""
    logger.error("500 error on path: %s", request.path)
    return render(request, '500.html', status=500)


@require_http_methods(["GET"])
def error_403(request, reason=''):
    """Render custom 403 page."""
    logger.warning("403 error on path: %s. Reason: %s", request.path, reason)
    return render(request, '403.html', status=403)
