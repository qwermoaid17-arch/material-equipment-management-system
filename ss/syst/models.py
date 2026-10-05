from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import AbstractUser



class User(AbstractUser):
    ROLE_CHOICES = (
        ('SUPER_ADMIN', 'الإدارة العامة'),
        ('SITE_ADMIN', 'مدير موقع'),
    )
    role = models.CharField('الصلاحية', max_length=20, choices=ROLE_CHOICES, default='SITE_ADMIN')
    site = models.ForeignKey('Site', on_delete=models.SET_NULL, null=True, blank=True,
                             related_name='users', verbose_name='الموقع')


    groups = models.ManyToManyField('auth.Group', related_name='custom_user_set',
                                    blank=True, verbose_name='المجموعات')
    user_permissions = models.ManyToManyField('auth.Permission', related_name='custom_user_set_permissions',
                                              blank=True, verbose_name='صلاحيات المستخدم')

    class Meta:
        verbose_name = 'مستخدم'
        verbose_name_plural = 'المستخدمون'



class Site(models.Model):
    name = models.CharField(max_length=150, verbose_name="اسم الموقع")
    location_code = models.CharField(max_length=50, unique=True, verbose_name="رمز الموقع")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإضافة')

    class Meta:
        verbose_name = 'موقع'
        verbose_name_plural = 'المواقع'

    def __str__(self):
        return self.name



class Item(models.Model):
    ITEM_TYPES = (
        ('MATERIAL', 'مادة بناء'),
        ('EQUIPMENT', 'معدة/آلة'),
        ('TOOL', 'أداة عمل'),
    )
    name = models.CharField(max_length=150, verbose_name="اسم المادة/المعدة")
    sku = models.CharField(max_length=50, unique=True, verbose_name="الرمز المرجعي")
    item_type = models.CharField(max_length=20, choices=ITEM_TYPES, verbose_name='نوع الصنف')
    unit = models.CharField(max_length=30, verbose_name="وحدة القياس")  # مثال: كيس، قطعة، متر

    class Meta:
        verbose_name = 'صنف'
        verbose_name_plural = 'الأصناف'

    def __str__(self):
        return self.name



class SiteInventory(models.Model):
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='inventory', verbose_name='الموقع')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, verbose_name='الصنف')
    quantity_available = models.PositiveIntegerField(default=0, verbose_name="الكمية المتاحة")
    quantity_surplus = models.PositiveIntegerField(default=0, verbose_name="الكمية الزائدة للطلب")

    class Meta:
        unique_together = ('site', 'item')
        verbose_name = 'مخزون موقع'
        verbose_name_plural = 'مخزون المواقع'

    def clean(self):
        if self.quantity_surplus > self.quantity_available:
            raise ValidationError('الكمية الزائدة لا يمكن أن تتجاوز الكمية المتاحة')

    def __str__(self):
        return f'{self.item} — {self.site}'



class TransferRequest(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'بانتظار الموافقة'),
        ('APPROVED', 'مقبول'),
        ('IN_TRANSIT', 'جاري النقل'),
        ('DELIVERED', 'تم الاستلام'),
        ('REJECTED', 'مرفوض'),
    )
    source_site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='transfers_sent', verbose_name='من موقع (المصدر)')
    target_site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='transfers_received', verbose_name='إلى موقع (المستلم)')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, verbose_name='الصنف')
    quantity = models.PositiveIntegerField(verbose_name='الكمية')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING', verbose_name='الحالة')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='أنشأه')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='تاريخ الإنشاء')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='آخر تحديث')

    class Meta:
        verbose_name = 'طلب نقل'
        verbose_name_plural = 'طلبات النقل'

    def __str__(self):
        return f'طلب #{self.pk} — {self.item} ({self.quantity})'



class TransferLog(models.Model):
    transfer = models.ForeignKey(TransferRequest, on_delete=models.CASCADE, verbose_name='طلب النقل')
    action_by = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='بواسطة')
    status_changed_to = models.CharField(max_length=20, verbose_name='الحالة الجديدة')
    note = models.TextField(blank=True, null=True, verbose_name='ملاحظة')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='الوقت')

    class Meta:
        verbose_name = 'سجل حركة'
        verbose_name_plural = 'سجل الحركة'

    def __str__(self):
        return f'{self.transfer} → {self.status_changed_to}'



class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications', verbose_name='المستخدم')
    title = models.CharField(max_length=200, verbose_name='العنوان')
    message = models.TextField(verbose_name='النص')
    is_read = models.BooleanField(default=False, verbose_name='مقروء')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='التاريخ')

    class Meta:
        verbose_name = 'إشعار'
        verbose_name_plural = 'الإشعارات'

    def __str__(self):
        return self.title
