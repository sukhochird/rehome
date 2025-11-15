from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class CreditTransaction(models.Model):
    TRANSACTION_TYPES = [
        ('add', 'Add Credits'),
        ('use', 'Use Credits'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credit_transactions')
    amount = models.IntegerField()
    transaction_type = models.CharField(max_length=3, choices=TRANSACTION_TYPES)
    description = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.transaction_type} {self.amount} credits"


class GeneratedImage(models.Model):
    STYLE_CHOICES = [
        ('modern', 'Modern'),
        ('minimal', 'Minimal'),
        ('luxury', 'Luxury'),
        ('rustic', 'Rustic'),
        ('industrial', 'Industrial'),
        ('scandinavian', 'Scandinavian'),
        ('bohemian', 'Bohemian'),
        ('traditional', 'Traditional'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='generated_images')
    original_image = models.ImageField(upload_to='original_images/')
    generated_image = models.ImageField(upload_to='generated_images/')
    style = models.CharField(max_length=50)
    room_type = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.style} style - {self.created_at}"


class OTPCode(models.Model):
    """OTP code for phone/email verification"""
    phone_or_email = models.CharField(max_length=255, db_index=True)
    otp_code = models.CharField(max_length=6)
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['phone_or_email', 'is_used']),
        ]
    
    def __str__(self):
        return f"{self.phone_or_email} - {self.otp_code}"
    
    def is_expired(self):
        from django.utils import timezone
        return timezone.now() > self.expires_at


class Package(models.Model):
    """Credit packages available for purchase"""
    name = models.CharField(max_length=100)
    credits = models.IntegerField(help_text="Number of credits in this package")
    price = models.IntegerField(help_text="Price in MNT")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['price']
    
    def __str__(self):
        return f"{self.name} - {self.credits} credits ({self.price} MNT)"


class Order(models.Model):
    """Orders for credit packages"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='orders')
    package = models.ForeignKey(Package, on_delete=models.CASCADE, related_name='orders')
    amount = models.IntegerField(help_text="Price in MNT")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    qpay_invoice_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    qpay_invoice_code = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.id} - {self.user.username} - {self.package.name} - {self.status}"


@receiver(post_save, sender=User)
def create_user_credits(sender, instance, created, **kwargs):
    """Automatically give new users 3 free credits"""
    if created:
        CreditTransaction.objects.create(
            user=instance,
            amount=3,
            transaction_type='add',
            description='Welcome bonus - 3 free credits'
        )