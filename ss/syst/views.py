from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.shortcuts import render
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import User, Site, Item, SiteInventory, TransferRequest, TransferLog, Notification
from .serializers import (SiteSerializer, ItemSerializer, SiteInventorySerializer,
                          TransferRequestSerializer, NotificationSerializer)


def is_super(user):
    return bool(getattr(user, 'is_superuser', False)) or getattr(user, 'role', None) == 'SUPER_ADMIN'

def send_notifications(site_ids, actor, title, site_message, admin_message):
    site_user_ids = []
    for u in User.objects.filter(site_id__in=site_ids).exclude(id=actor.id):
        Notification.objects.create(user=u, title=title, message=site_message)
        site_user_ids.append(u.id)

    for u in User.objects.filter(role='SUPER_ADMIN').exclude(id__in=site_user_ids):
        Notification.objects.create(user=u, title=f'[إشراف] {title}', message=admin_message)

class SiteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Site.objects.all()
    serializer_class = SiteSerializer
    permission_classes = [IsAuthenticated]


class ItemViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    permission_classes = [IsAuthenticated]


class SiteInventoryViewSet(viewsets.ModelViewSet):
    serializer_class = SiteInventorySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        qs = SiteInventory.objects.select_related('site', 'item')
        if is_super(user):
            return qs

        return qs.filter(site=user.site) if user.site_id else qs.none()

    def perform_create(self, serializer):
        user = self.request.user
        if is_super(user):
            site = serializer.validated_data.get('site')
            if not site:
                raise ValidationError({'site': 'اختر الموقع'})
        else:
            if not user.site_id:
                raise PermissionDenied('لا يوجد موقع مرتبط بحسابك')
            site = user.site       

        item = serializer.validated_data['item']
        if SiteInventory.objects.filter(site=site, item=item).exists():
            raise ValidationError('هذا الصنف موجود مسبقاً في المخزون، عدّل كميته بدل إضافته مرة أخرى')
        serializer.save(site=site)

    def perform_update(self, serializer):

        if is_super(self.request.user):
            serializer.save()
        else:
            serializer.save(site=serializer.instance.site)

    def perform_destroy(self, instance):
        if not is_super(self.request.user):
            raise PermissionDenied('الحذف للإدارة العامة فقط')
        instance.delete()

    @action(detail=False, methods=['get'])
    def surplus(self, request):

        qs = SiteInventory.objects.select_related('site', 'item').filter(quantity_surplus__gt=0)
        if not is_super(request.user) and request.user.site_id:
            qs = qs.exclude(site=request.user.site)
        data = [{
            'id': i.id, 'site': i.site_id, 'site_name': i.site.name,
            'item': i.item_id, 'item_name': i.item.name, 'item_sku': i.item.sku,
            'item_unit': i.item.unit, 'quantity_surplus': i.quantity_surplus,
        } for i in qs]
        return Response(data)


class TransferRequestViewSet(viewsets.ModelViewSet):
    serializer_class = TransferRequestSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        qs = TransferRequest.objects.select_related('source_site', 'target_site', 'item', 'created_by')
        if is_super(user):
            return qs.order_by('-created_at')
        if user.site_id:
            return qs.filter(Q(source_site=user.site) | Q(target_site=user.site)).order_by('-created_at')
        return qs.none()

    def perform_create(self, serializer):
        user = self.request.user
        d = serializer.validated_data
        if is_super(user):
            source, target = d['source_site'], d['target_site']
        else:
            if not user.site_id:
                raise PermissionDenied('لا يوجد موقع مرتبط بحسابك')
            source, target = d['source_site'], user.site 
        if source.id == target.id:
            raise ValidationError('لا يمكن النقل إلى نفس الموقع')
        inv = SiteInventory.objects.filter(site=source, item=d['item']).first()
        if not inv or inv.quantity_surplus < d['quantity']:
            raise ValidationError('الكمية المطلوبة أكبر من الكمية الزائدة المتاحة في الموقع المصدر')
        tr = serializer.save(created_by=user, target_site=target)
        TransferLog.objects.create(transfer=tr, action_by=user, status_changed_to='PENDING', note='إنشاء الطلب')
        send_notifications(
            [source.id], user, 'طلب نقل جديد',
            f'طلب {tr.quantity} {tr.item.name} من موقعكم إلى {target.name}',
            f'{user.username} أنشأ طلباً لنقل {tr.quantity} {tr.item.name} '
            f'من {source.name} إلى {target.name}'
        )

    @action(detail=True, methods=['post'])
    def change_status(self, request, pk=None):
        tr = self.get_object()
        user = request.user
        new = request.data.get('status')
        note = request.data.get('note', '')
        rules = {
            'APPROVED': ('PENDING', tr.source_site_id),
            'REJECTED': ('PENDING', tr.source_site_id),
            'IN_TRANSIT': ('APPROVED', tr.source_site_id),
            'DELIVERED': ('IN_TRANSIT', tr.target_site_id),
        }
        if new not in rules:
            raise ValidationError('حالة غير صحيحة')
        prev, owner_site = rules[new]
        if tr.status != prev:
            raise ValidationError('لا يمكن تغيير الحالة من وضعها الحالي')
        if not is_super(user) and user.site_id != owner_site:
            raise PermissionDenied('ليست لديك صلاحية لهذا الإجراء')

        with transaction.atomic():
            src = SiteInventory.objects.select_for_update().filter(
                site=tr.source_site, item=tr.item).first()

            if new == 'APPROVED':

                if not src or src.quantity_surplus < tr.quantity:
                    raise ValidationError('الكمية الزائدة المتاحة أقل من الكمية المطلوبة')
                src.quantity_surplus -= tr.quantity
                src.save()

            elif new == 'DELIVERED':

                if not src or src.quantity_available < tr.quantity:
                    raise ValidationError('الكمية غير متوفرة في الموقع المصدر')
                src.quantity_available -= tr.quantity
                src.save()
                dst, _ = SiteInventory.objects.select_for_update().get_or_create(
                    site=tr.target_site, item=tr.item)
                dst.quantity_available += tr.quantity
                dst.save()

            tr.status = new
            tr.save()
            TransferLog.objects.create(transfer=tr, action_by=user, status_changed_to=new, note=note)
            label = dict(TransferRequest.STATUS_CHOICES)[new]
            send_notifications(
                [tr.source_site_id, tr.target_site_id], user, 'تحديث على طلب نقل',
                f'{tr.item.name} ({tr.quantity}) : {label}',
                f'{user.username} غيّر حالة الطلب رقم {tr.id} ({tr.item.name} × {tr.quantity}) '
                f'من {tr.source_site.name} إلى {tr.target_site.name}، الحالة الجديدة: {label}'
            )
        return Response(self.get_serializer(tr).data)

    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        tr = self.get_object()
        return Response([{'status': l.status_changed_to, 'by': l.action_by.username,
                          'note': l.note, 'time': l.timestamp} for l in tr.transferlog_set.order_by('timestamp')])


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user).order_by('-created_at')

    @action(detail=False, methods=['post'])
    def read_all(self, request):
        self.get_queryset().update(is_read=True)
        return Response({'ok': True})

    @action(detail=True, methods=['post'])
    def read(self, request, pk=None):
        n = self.get_object()
        n.is_read = True
        n.save()
        return Response({'ok': True})



@login_required
def dashboard_view(request):
    return render(request, 'syst/dashboard.html')

@login_required
def inventory_page(request):
    return render(request, 'syst/inventory.html')

@login_required
def transfers_page(request):
    return render(request, 'syst/transfers.html')

@login_required
def notifications_page(request):
    return render(request, 'syst/notifications.html')
