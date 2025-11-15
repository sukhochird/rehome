from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Sum
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from datetime import timedelta
import requests
import io
from PIL import Image
import os
import uuid
from google import genai
from io import BytesIO
import base64
import random
import re
import json

from .models import CreditTransaction, GeneratedImage, OTPCode, Package, Order
from .serializers import (
    UserSerializer, CreditTransactionSerializer, 
    GeneratedImageSerializer, ImageGenerationSerializer,
    PurchaseCreditsSerializer, PackageSerializer, OrderSerializer
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


# QPay Integration Functions
def get_qpay_access_token():
    """Get QPay access token"""
    url = "https://merchant.qpay.mn/v2/auth/token"
    response = requests.post(
        url, 
        auth=(settings.QPAY_USERNAME, settings.QPAY_PASSWORD)
    )
    if response.status_code == 200:
        return json.loads(response.text)['access_token']
    else:
        raise Exception(f"Failed to get QPay access token: {response.text}")


def create_qpay_invoice(order):
    """Create QPay invoice for an order"""
    try:
        access_token = get_qpay_access_token()
        bearer_token = f"Bearer {access_token}"
        url = "https://merchant.qpay.mn/v2/invoice"
        
        # Get the base URL from request (we'll pass it from view)
        # For now, use a placeholder that will be replaced
        callback_url = f"{settings.QPAY_CALLBACK_BASE_URL}/api/qpay-webhook/?invoiceid={order.id}"
        
        request_body = {
            "invoice_code": settings.QPAY_INVOICE_CODE,
            "sender_invoice_no": str(order.id),
            "invoice_receiver_code": "terminal",
            "invoice_description": f"ReHome - {order.package.name} багц ({order.package.credits} кредит)",
            "sender_branch_code": "Credits",
            "amount": str(int(order.amount)),
            "callback_url": callback_url
        }
        
        request_headers = {
            'Content-Type': 'application/json',
            'Authorization': bearer_token,
        }
        
        response = requests.post(
            url, 
            headers=request_headers, 
            data=json.dumps(request_body)
        )
        
        if response.status_code == 200:
            response_json = json.loads(response.text)
            return response_json
        else:
            raise Exception(f"Failed to create QPay invoice: {response.text}")
    except Exception as e:
        raise Exception(f"QPay invoice creation error: {str(e)}")


class PackageListView(APIView):
    """List all active credit packages"""
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        packages = Package.objects.filter(is_active=True)
        return Response({
            'packages': PackageSerializer(packages, many=True).data
        })


class PurchaseCreditsView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        package_id = request.data.get('package_id')
        
        if not package_id:
            return Response({
                'error': 'package_id шаардлагатай'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            package = Package.objects.get(id=package_id, is_active=True)
        except Package.DoesNotExist:
            return Response({
                'error': 'Багц олдсонгүй'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Create order
        order = Order.objects.create(
            user=request.user,
            package=package,
            amount=package.price,
            status='pending'
        )
        
        try:
            # Create QPay invoice
            qpay_response = create_qpay_invoice(order)
            
            # Update order with QPay invoice info
            order.qpay_invoice_id = qpay_response.get('invoice_id')
            order.qpay_invoice_code = qpay_response.get('invoice_id')  # Using invoice_id as code
            order.save()
            
            return Response({
                'message': 'QPay invoice амжилттай үүслээ',
                'order': OrderSerializer(order).data,
                'qpay_invoice': {
                    'invoice_id': qpay_response.get('invoice_id'),
                    'qr_text': qpay_response.get('qr_text'),
                    'qr_image': qpay_response.get('qr_image'),
                    'qPay_shortUrl': qpay_response.get('qPay_shortUrl'),
                    'urls': qpay_response.get('urls', [])
                }
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            order.status = 'failed'
            order.save()
            return Response({
                'error': f'QPay invoice үүсгэхэд алдаа гарлаа: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
def send_otp_view(request):
    """Send OTP code to phone or email"""
    phone_or_email = request.data.get('phone_or_email', '').strip()
    
    if not phone_or_email:
        return Response({
            'error': 'Утасны дугаар эсвэл имэйл оруулна уу'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Validate phone number format (for signup, only phone is allowed)
    # For login, we allow both phone and email
    is_email = '@' in phone_or_email
    if not is_email:
        # Validate phone number (only digits, 8-10 digits)
        phone_regex = re.compile(r'^[0-9]{8,10}$')
        if not phone_regex.match(phone_or_email):
            return Response({
                'error': 'Утасны дугаар зөв биш байна. Зөвхөн тоо оруулна уу (8-10 орон)'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Generate OTP code (for testing, always use 123456)
    otp_code = '123456'
    
    # In production, you would generate a random code:
    # otp_code = str(random.randint(100000, 999999))
    
    # Set expiration time (5 minutes)
    expires_at = timezone.now() + timedelta(minutes=5)
    
    # Mark old OTP codes as used
    OTPCode.objects.filter(
        phone_or_email=phone_or_email,
        is_used=False
    ).update(is_used=True)
    
    # Create new OTP code
    otp = OTPCode.objects.create(
        phone_or_email=phone_or_email,
        otp_code=otp_code,
        expires_at=expires_at
    )
    
    # Fake SMS API - just log it (in production, send real SMS)
    print(f"[FAKE SMS] Sending OTP {otp_code} to {phone_or_email}")
    
    return Response({
        'message': 'OTP код илгээгдлээ',
        'otp_code': otp_code  # Only for testing, remove in production
    })


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def verify_otp_view(request):
    """Verify OTP code and login/signup user"""
    phone_or_email = request.data.get('phone_or_email', '').strip()
    otp_code = request.data.get('otp_code', '').strip()
    username = request.data.get('username', '').strip()
    
    if not phone_or_email or not otp_code:
        return Response({
            'error': 'Утасны дугаар/имэйл болон OTP код оруулна уу'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Find valid OTP code
    try:
        otp = OTPCode.objects.filter(
            phone_or_email=phone_or_email,
            otp_code=otp_code,
            is_used=False
        ).order_by('-created_at').first()
        
        if not otp:
            return Response({
                'error': 'OTP код буруу байна'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if otp.is_expired():
            return Response({
                'error': 'OTP код хүчинтэй хугацаа дууссан'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Mark OTP as used
        otp.is_used = True
        otp.save()
        
        # Check if user exists
        is_email = '@' in phone_or_email
        if is_email:
            user = User.objects.filter(email=phone_or_email).first()
        else:
            # For phone, we'll use email field to store phone
            user = User.objects.filter(email=phone_or_email).first()
        
        if user:
            # Login existing user
            login(request, user)
            return Response({
                'message': 'Амжилттай нэвтэрлээ',
                'user': UserSerializer(user).data
            })
        else:
            # Signup new user
            if not username:
                # Generate username from phone/email
                if is_email:
                    username = phone_or_email.split('@')[0]
                else:
                    username = f"user_{phone_or_email[-4:]}"
            
            # Check if username already exists
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1
            
            # Create new user
            user = User.objects.create_user(
                username=username,
                email=phone_or_email if is_email else phone_or_email,
                password=None  # No password for OTP-based auth
            )
            
            # Set a random password (required by Django)
            user.set_unusable_password()
            user.save()
            
            login(request, user)
            
            return Response({
                'message': 'Бүртгэл амжилттай үүслээ',
                'user': UserSerializer(user).data
            }, status=status.HTTP_201_CREATED)
            
    except Exception as e:
        return Response({
            'error': f'Алдаа гарлаа: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    """Legacy login view - kept for backward compatibility but redirects to OTP"""
    return Response({
        'error': 'OTP код ашиглана уу',
        'message': 'Энэ endpoint ашиглахгүй болсон. /api/send-otp/ болон /api/verify-otp/ ашиглана уу.'
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def logout_view(request):
    logout(request)
    return Response({'message': 'Logout successful'})


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def signup_view(request):
    """Legacy signup view - kept for backward compatibility but redirects to OTP"""
    return Response({
        'error': 'OTP код ашиглана уу',
        'message': 'Энэ endpoint ашиглахгүй болсон. /api/send-otp/ болон /api/verify-otp/ ашиглана уу.'
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@permission_classes([permissions.AllowAny])
def qpay_webhook_view(request):
    """QPay webhook to handle payment confirmations"""
    from django.http import HttpResponse
    
    # Get invoice ID from query parameter or request body
    invoice_id = request.GET.get('invoiceid') or request.data.get('invoiceid')
    
    if not invoice_id:
        return HttpResponse('invoiceid шаардлагатай', status=400)
    
    try:
        # Try to find order by order.id (sender_invoice_no) or qpay_invoice_id
        try:
            order = Order.objects.get(id=int(invoice_id), status='pending')
        except (Order.DoesNotExist, ValueError):
            # If not found by order.id, try by qpay_invoice_id
            order = Order.objects.get(qpay_invoice_id=invoice_id, status='pending')
    except Order.DoesNotExist:
        return HttpResponse('Order олдсонгүй эсвэл аль хэдийн боловсруулагдсан', status=404)
    
    # Verify payment with QPay
    if not order.qpay_invoice_id:
        return HttpResponse('Order дээр QPay invoice ID байхгүй байна', status=400)
    
    try:
        access_token = get_qpay_access_token()
        bearer_token = f"Bearer {access_token}"
        
        # Check invoice status
        check_url = f"https://merchant.qpay.mn/v2/payment/check"
        check_headers = {
            'Content-Type': 'application/json',
            'Authorization': bearer_token,
        }
        check_body = {
            "object_type": "INVOICE",
            "object_id": order.qpay_invoice_id
        }
        
        check_response = requests.post(
            check_url,
            headers=check_headers,
            data=json.dumps(check_body)
        )
        
        if check_response.status_code == 200:
            check_data = json.loads(check_response.text)
            
            # Check if payment was successful
            if check_data.get('paid_amount', 0) >= order.amount:
                # Update order status
                order.status = 'paid'
                order.save()
                
                # Add credits to user account
                CreditTransaction.objects.create(
                    user=order.user,
                    amount=order.package.credits,
                    transaction_type='add',
                    description=f'Purchased {order.package.name} package - {order.package.credits} credits'
                )
                
                return HttpResponse('qPay_webHookTest')
            else:
                return HttpResponse('Төлбөр хангалтгүй байна', status=400)
        else:
            return HttpResponse(f'QPay төлбөрийн статус шалгахэд алдаа: {check_response.text}', status=500)
            
    except Exception as e:
        return HttpResponse(f'Webhook боловсруулах явцад алдаа: {str(e)}', status=500)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def check_order_status_view(request):
    """Check order payment status"""
    order_id = request.GET.get('order_id')
    
    if not order_id:
        return Response({
            'error': 'order_id шаардлагатай'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        order = Order.objects.get(id=int(order_id), user=request.user)
        return Response({
            'order_id': order.id,
            'status': order.status,
            'is_paid': order.status == 'paid',
            'credits': order.package.credits if order.status == 'paid' else 0
        })
    except Order.DoesNotExist:
        return Response({
            'error': 'Order олдсонгүй'
        }, status=status.HTTP_404_NOT_FOUND)
    except ValueError:
        return Response({
            'error': 'Буруу order_id'
        }, status=status.HTTP_400_BAD_REQUEST)