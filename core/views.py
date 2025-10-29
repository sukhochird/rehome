from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Sum
from django.conf import settings
from django.core.files.base import ContentFile
import openai
import requests
import io
from PIL import Image
import os
import uuid
from google import genai
from google.genai import types

from .models import CreditTransaction, GeneratedImage
from .serializers import (
    UserSerializer, CreditTransactionSerializer, 
    GeneratedImageSerializer, ImageGenerationSerializer,
    PurchaseCreditsSerializer
)


class UserProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class UserDashboardView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Calculate credit balance
        total_added = CreditTransaction.objects.filter(
            user=user, transaction_type='add'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_used = CreditTransaction.objects.filter(
            user=user, transaction_type='use'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        credit_balance = total_added - total_used
        
        # Get recent transactions
        recent_transactions = CreditTransaction.objects.filter(
            user=user
        ).order_by('-created_at')[:10]
        
        # Get generated images
        generated_images = GeneratedImage.objects.filter(
            user=user
        ).order_by('-created_at')
        
        return Response({
            'user': UserSerializer(user).data,
            'credit_balance': credit_balance,
            'recent_transactions': CreditTransactionSerializer(recent_transactions, many=True).data,
            'generated_images': GeneratedImageSerializer(generated_images, many=True).data,
        })


class PurchaseCreditsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = PurchaseCreditsSerializer(data=request.data)
        if serializer.is_valid():
            amount = serializer.validated_data['amount']
            
            # Create credit transaction
            CreditTransaction.objects.create(
                user=request.user,
                amount=amount,
                transaction_type='add',
                description=f'Purchased {amount} credits for 5,000 MNT'
            )
            
            return Response({
                'message': f'Successfully purchased {amount} credits!',
                'credits_added': amount
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RecentImagesView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Get user's most recent 3 uploaded images
        recent_images = GeneratedImage.objects.filter(
            user=request.user
        ).order_by('-created_at')[:3]
        
        return Response({
            'recent_images': GeneratedImageSerializer(recent_images, many=True).data
        })


class GenerateImageView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Check if user has credits
        total_added = CreditTransaction.objects.filter(
            user=request.user, transaction_type='add'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        total_used = CreditTransaction.objects.filter(
            user=request.user, transaction_type='use'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        credit_balance = total_added - total_used
        
        if credit_balance < 1:
            return Response({
                'error': 'Insufficient credits. Please purchase more credits to generate images.'
            }, status=status.HTTP_402_PAYMENT_REQUIRED)
        
        serializer = ImageGenerationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        image = serializer.validated_data['image']
        style = serializer.validated_data['style']
        room_type = serializer.validated_data.get('room_type', '')
        description = serializer.validated_data.get('description', '')
        
        try:
            # Initialize Google Gemini client
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            # Open the uploaded image
            uploaded_image = Image.open(image)
            
            # Create detailed prompt for Gemini with inpainting
            prompt_parts = [
                f"Using the provided image of a {room_type if room_type else 'room'} interior,",
                f"change the entire room design to {style} style.",
                "Keep the exact room layout, floor plan, windows and doors positions unchanged.",
                "Preserve the architectural elements, dimensions, and proportions.",
                "Maintain realistic proportions, natural lighting, and professional interior design quality.",
                "Only change the furniture, decor, colors, materials, and styling while keeping all structural elements identical."
            ]
            
            if description:
                prompt_parts.insert(-1, f"Following these specific requirements: {description}")
            
            text_input = " ".join(prompt_parts)
            
            # Generate image using Gemini with inpainting
            response = client.models.generate_content(
                model="gemini-2.5-flash-image",
                contents=[uploaded_image, text_input],
            )
            
            # Extract image data from response
            image_parts = [
                part.inline_data.data
                for part in response.candidates[0].content.parts
                if part.inline_data
            ]
            
            if not image_parts:
                raise Exception("No image data received from Gemini API")
            
            # Save the generated image
            generated_image_name = f"generated_{uuid.uuid4().hex}.png"
            generated_image_file = ContentFile(image_parts[0], name=generated_image_name)
            
            # Create GeneratedImage instance
            generated_image = GeneratedImage.objects.create(
                user=request.user,
                original_image=image,
                generated_image=generated_image_file,
                style=style,
                room_type=room_type,
                description=description
            )
            
            # Deduct credit
            CreditTransaction.objects.create(
                user=request.user,
                amount=1,
                transaction_type='use',
                description=f'Generated {style} style image'
            )
            
            return Response({
                'message': 'Image generated successfully!',
                'generated_image': GeneratedImageSerializer(generated_image).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': f'Failed to generate image: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    if username and password:
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return Response({
                'message': 'Login successful',
                'user': UserSerializer(user).data
            })
        else:
            return Response({
                'error': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
    else:
        return Response({
            'error': 'Username and password required'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response({'message': 'Logout successful'})


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def signup_view(request):
    username = request.data.get('username')
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not all([username, email, password]):
        return Response({
            'error': 'Username, email, and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if User.objects.filter(username=username).exists():
        return Response({
            'error': 'Username already exists'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if User.objects.filter(email=email).exists():
        return Response({
            'error': 'Email already exists'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )
    
    # The post_save signal will automatically create 3 free credits
    
    return Response({
        'message': 'User created successfully',
        'user': UserSerializer(user).data
    }, status=status.HTTP_201_CREATED)