from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import CreditTransaction, GeneratedImage


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


admin.site.register(CreditTransaction, CreditTransactionAdmin)
admin.site.register(GeneratedImage, GeneratedImageAdmin)