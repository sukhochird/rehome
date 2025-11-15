from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import CreditTransaction, GeneratedImage, Package, Order


class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ['user', 'amount', 'transaction_type', 'description', 'created_at']
    list_filter = ['transaction_type', 'created_at']
    search_fields = ['user__username', 'description']
    readonly_fields = ['created_at']


class GeneratedImageAdmin(admin.ModelAdmin):
    list_display = ['user', 'style', 'created_at']
    list_filter = ['style', 'created_at']
    search_fields = ['user__username']
    readonly_fields = ['created_at']


class PackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'credits', 'price', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    readonly_fields = ['created_at']


class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'package', 'amount', 'status', 'qpay_invoice_id', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['user__username', 'qpay_invoice_id']
    readonly_fields = ['created_at', 'updated_at']


admin.site.register(CreditTransaction, CreditTransactionAdmin)
admin.site.register(GeneratedImage, GeneratedImageAdmin)
admin.site.register(Package, PackageAdmin)
admin.site.register(Order, OrderAdmin)