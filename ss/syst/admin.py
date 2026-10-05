from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.contrib.admin.sites import NotRegistered
from django.db.models import Count
from django.utils.html import format_html

from .models import User, Site, Item, SiteInventory, TransferRequest, TransferLog, Notification

admin.site.site_header = 'نظام إدارة المواد والمعدات'
admin.site.site_title = 'لوحة الإدارة'
admin.site.index_title = 'مرحباً بك في لوحة إدارة النظام'
admin.site.site_url = '/dashboard/'    


try:
    admin.site.unregister(Group)
except NotRegistered:
    pass

STATUS_COLORS = {
    'PENDING': '#f0ad00', 'APPROVED': '#17a2b8', 'IN_TRANSIT': '#0d6efd',
    'DELIVERED': '#198754', 'REJECTED': '#dc3545',
}


def badge(text, color):
    return format_html(
        '<span style="background:{};color:#fff;padding:3px 12px;border-radius:12px;'
        'font-size:12px;white-space:nowrap">{}</span>', color, text)



@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('البيانات الشخصية', {'fields': ('first_name', 'last_name', 'email')}),
        ('الصلاحية والموقع', {'fields': ('role', 'site')}),
        ('الحالة', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('تواريخ مهمة', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (('الصلاحية والموقع', {'fields': ('role', 'site')}),)
    list_display = ('username', 'get_full_name', 'role_badge', 'site', 'is_active')
    list_filter = ('role', 'site', 'is_active')
    search_fields = ('username', 'first_name', 'last_name', 'email')
    list_select_related = ('site',)

    @admin.display(description='الصلاحية', ordering='role')
    def role_badge(self, obj):
        return badge(obj.get_role_display(), '#1f3a5f' if obj.role == 'SUPER_ADMIN' else '#6c757d')



class SiteInventoryInline(admin.TabularInline):
    model = SiteInventory
    extra = 0
    fields = ('item', 'quantity_available', 'quantity_surplus')
    autocomplete_fields = ('item',)


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'location_code', 'users_count', 'items_count', 'created_at')
    search_fields = ('name', 'location_code')
    inlines = [SiteInventoryInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _users=Count('users', distinct=True), _items=Count('inventory', distinct=True))

    @admin.display(description='عدد المستخدمين', ordering='_users')
    def users_count(self, obj):
        return obj._users

    @admin.display(description='عدد الأصناف', ordering='_items')
    def items_count(self, obj):
        return obj._items



@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'item_type', 'unit')
    list_filter = ('item_type',)
    search_fields = ('name', 'sku')



@admin.register(SiteInventory)
class SiteInventoryAdmin(admin.ModelAdmin):
    list_display = ('item', 'site', 'quantity_available', 'quantity_surplus')
    list_editable = ('quantity_available', 'quantity_surplus')
    list_filter = ('site', 'item__item_type')
    search_fields = ('item__name', 'item__sku', 'site__name')
    list_select_related = ('item', 'site')
    autocomplete_fields = ('item',)



class TransferLogInline(admin.TabularInline):
    model = TransferLog
    extra = 0
    can_delete = False
    readonly_fields = ('status_changed_to', 'action_by', 'note', 'timestamp')

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(TransferRequest)
class TransferRequestAdmin(admin.ModelAdmin):
    list_display = ('id', 'item', 'quantity', 'source_site', 'target_site', 'status_badge', 'created_by', 'created_at')
    list_filter = ('status', 'source_site', 'target_site', 'created_at')
    search_fields = ('item__name', 'item__sku', 'source_site__name', 'target_site__name', 'created_by__username')
    date_hierarchy = 'created_at'
    list_select_related = ('item', 'source_site', 'target_site', 'created_by')
    readonly_fields = ('status', 'created_by', 'created_at', 'updated_at')
    inlines = [TransferLogInline]

    @admin.display(description='الحالة', ordering='status')
    def status_badge(self, obj):
        return badge(obj.get_status_display(), STATUS_COLORS.get(obj.status, '#6c757d'))


    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser



@admin.register(TransferLog)
class TransferLogAdmin(admin.ModelAdmin):
    list_display = ('transfer', 'status_badge', 'action_by', 'note', 'timestamp')
    list_filter = ('status_changed_to', 'timestamp')
    search_fields = ('transfer__item__name', 'action_by__username', 'note')
    date_hierarchy = 'timestamp'
    list_select_related = ('transfer__item', 'action_by')

    @admin.display(description='الحالة الجديدة', ordering='status_changed_to')
    def status_badge(self, obj):
        label = dict(TransferRequest.STATUS_CHOICES).get(obj.status_changed_to, obj.status_changed_to)
        return badge(label, STATUS_COLORS.get(obj.status_changed_to, '#6c757d'))

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False



@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('title', 'message', 'user__username')
    date_hierarchy = 'created_at'
    actions = ['mark_read', 'mark_unread']

    @admin.action(description='تحديد المحدد كمقروء')
    def mark_read(self, request, queryset):
        n = queryset.update(is_read=True)
        self.message_user(request, f'تم تحديد {n} إشعار كمقروء')

    @admin.action(description='تحديد المحدد كغير مقروء')
    def mark_unread(self, request, queryset):
        n = queryset.update(is_read=False)
        self.message_user(request, f'تم تحديد {n} إشعار كغير مقروء')
