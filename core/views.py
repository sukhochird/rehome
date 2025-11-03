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
from io import BytesIO
import base64

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
            # Save original image first
            original_image_file = None
            if image:
                # Reset file pointer to beginning
                image.seek(0)
                
                # Generate unique filename for original image
                original_image_name = f"original_{uuid.uuid4().hex}_{image.name}"
                
                # Read the file content and save it
                original_image_file = ContentFile(image.read(), name=original_image_name)
            
            # Open the uploaded image for processing
            image.seek(0)  # Reset file pointer
            uploaded_image = Image.open(image)
            
            # Convert to RGB if necessary (remove alpha channel for compatibility)
            if uploaded_image.mode in ('RGBA', 'LA'):
                rgb_image = Image.new('RGB', uploaded_image.size, (255, 255, 255))
                rgb_image.paste(uploaded_image, mask=uploaded_image.split()[-1] if uploaded_image.mode == 'RGBA' else None)
                uploaded_image = rgb_image
            
            # Save image to bytes for API
            image_bytes = io.BytesIO()
            uploaded_image.save(image_bytes, format='PNG')
            image_bytes.seek(0)
            
            # Convert image for Gemini
            image_bytes.seek(0)
            pil_image = Image.open(image_bytes)
            
            # Create comprehensive prompt for Gemini 2.5 Flash Image
            text_input = f"""Using the provided image of a {room_type if room_type else 'room'} interior, change the entire room design to {style} style. Keep the exact room layout, floor plan, windows and doors positions unchanged. Preserve the architectural elements, dimensions, and proportions. Maintain realistic proportions, natural lighting, and professional interior design quality. Only change the furniture, decor, colors, materials, and styling while keeping all structural elements identical."""
            
            if description:
                text_input += f" Additional requirements: {description}"
            
            # Use Gemini 2.5 Flash Image API with the correct client format
            generated_image_file = None
            
            try:
                # Initialize Gemini client
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                
                # Generate image using the client
                response = client.models.generate_content(
                    model="gemini-2.5-flash-image",
                    contents=[text_input, pil_image],
                )
                
                # Extract image from response
                image_parts = [
                    part.inline_data.data
                    for part in response.candidates[0].content.parts
                    if part.inline_data
                ]
                
                if image_parts:
                    # Convert to PIL Image and then to ContentFile
                    image = Image.open(BytesIO(image_parts[0]))
                    
                    # Save to BytesIO buffer
                    output_buffer = BytesIO()
                    image.save(output_buffer, format='PNG')
                    output_buffer.seek(0)
                    
                    # Create ContentFile
                    generated_image_file = ContentFile(
                        output_buffer.read(),
                        name=f"generated_{uuid.uuid4().hex}.png"
                    )
                else:
                    raise Exception("No image data found in API response")
                        
            except Exception as e:
                # If generation fails, raise the exception with details
                raise Exception(f"Failed to generate image with Gemini: {str(e)}")
            
            if not generated_image_file:
                raise Exception("No image was generated. Please check your API key and model availability.")
            
            # Verify generated image file has content
            generated_image_file.seek(0, 2)  # Seek to end
            file_size = generated_image_file.tell()
            generated_image_file.seek(0)  # Reset to beginning
            
            if file_size == 0:
                raise Exception("Generated image file is empty. Please check the API response.")
            
            # Ensure we have original image file
            if not original_image_file:
                # Fallback: create from processed image
                image_bytes.seek(0)
                original_image_name = f"original_{uuid.uuid4().hex}.png"
                original_image_file = ContentFile(image_bytes.read(), name=original_image_name)
            
            # Reset file pointers before saving
            generated_image_file.seek(0)
            if hasattr(original_image_file, 'seek'):
                original_image_file.seek(0)
            
            # Create GeneratedImage instance and save both images
            try:
                generated_image = GeneratedImage.objects.create(
                    user=request.user,
                    original_image=original_image_file,
                    generated_image=generated_image_file,
                    style=style,
                    room_type=room_type,
                    description=description
                )
                
                # Ensure the instance is saved properly and files are written
                generated_image.save()
                
                # Verify the saved file
                if hasattr(generated_image.generated_image, 'size') and generated_image.generated_image.size == 0:
                    raise Exception("Saved generated image file is empty after save operation.")
                
            except Exception as save_error:
                raise Exception(f"Failed to save generated image: {str(save_error)}")
            
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
    
    # The post_save signal will automatically create 300 free credits
    
    return Response({
        'message': 'User created successfully',
        'user': UserSerializer(user).data
    }, status=status.HTTP_201_CREATED)