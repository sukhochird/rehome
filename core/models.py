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


@receiver(post_save, sender=User)
def create_user_credits(sender, instance, created, **kwargs):
    """Automatically give new users 300 free credits"""
    if created:
        CreditTransaction.objects.create(
            user=instance,
            amount=300,
            transaction_type='add',
            description='Welcome bonus - 300 free credits'
        )