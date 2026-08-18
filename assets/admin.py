from django.contrib import admin
from .models import Category, Asset, ChangeHistory, SecurityLog


class ReadOnlyAdmin(admin.ModelAdmin):
    """Admin interface for read-only models (audit logs)."""
    
    def has_add_permission(self, request):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


class SecurityLogAdmin(ReadOnlyAdmin):
    """Display security events for audit trail."""
    readonly_fields = ['user', 'created_at', 'ip_address', 'user_agent', 'event_type', 'description']
    list_display = ['get_event_type_display', 'get_username', 'ip_address', 'created_at']
    list_filter = ['event_type', 'created_at', 'user']
    search_fields = ['user__username', 'ip_address', 'description']
    ordering = ['-created_at']
    
    def get_username(self, obj):
        return obj.user.username if obj.user else 'System'
    get_username.short_description = 'Użytkownik'


class ChangeHistoryAdmin(ReadOnlyAdmin):
    """Display change history for audit trail."""
    readonly_fields = ['user', 'created_at', 'action', 'model_name', 'object_name', 'description']
    list_display = ['get_action_display', 'model_name', 'object_name', 'get_username', 'created_at']
    list_filter = ['action', 'model_name', 'created_at', 'user']
    search_fields = ['user__username', 'object_name', 'model_name', 'description']
    ordering = ['-created_at']
    
    def get_username(self, obj):
        return obj.user.username if obj.user else 'System'
    get_username.short_description = 'Użytkownik'


admin.site.register(Category)
admin.site.register(Asset)
admin.site.register(SecurityLog, SecurityLogAdmin)
admin.site.register(ChangeHistory, ChangeHistoryAdmin)