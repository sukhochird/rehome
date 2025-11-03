from rest_framework import serializers
from django.contrib.auth.models import User
from django.db.models import Sum
from .models import CreditTransaction, GeneratedImage


class UserSerializer(serializers.ModelSerializer):
    credit_balance = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'credit_balance', 'date_joined']
        read_only_fields = ['id', 'credit_balance', 'date_joined']
    
    def get_credit_balance(self, obj):
        """Calculate user's current credit balance"""
        total_added = CreditTransaction.objects.filter(
            user=obj, transaction_type='add'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_used = CreditTransaction.objects.filter(
            user=obj, transaction_type='use'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        return total_added - total_used


class CreditTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditTransaction
        fields = ['id', 'amount', 'transaction_type', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class GeneratedImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedImage
        fields = ['id', 'original_image', 'generated_image', 'style', 'room_type', 'description', 'created_at']
        read_only_fields = ['id', 'created_at']


class ImageGenerationSerializer(serializers.Serializer):
    image = serializers.ImageField()
    style = serializers.CharField()
    room_type = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)


class PurchaseCreditsSerializer(serializers.Serializer):
    amount = serializers.IntegerField(default=10)
