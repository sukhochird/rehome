from django.urls import path
from . import views, views_frontend

app_name = 'core'

urlpatterns = [
    # Frontend pages
    path('', views_frontend.landing_view, name='landing'),
    path('app/', views_frontend.index_view, name='home'),
    path('app/profile/', views_frontend.profile_view, name='profile_page'),
    path('login/', views_frontend.login_page, name='login_page'),  # Redirects to landing with modal
    path('signup/', views_frontend.signup_page, name='signup_page'),  # Redirects to landing with modal
    path('logout/', views_frontend.logout_view, name='logout'),
    
    # API endpoints
    path('api/login/', views.login_view, name='login'),
    path('api/logout/', views.logout_view, name='logout'),
    path('api/signup/', views.signup_view, name='signup'),
    path('api/send-otp/', views.send_otp_view, name='send_otp'),
    path('api/verify-otp/', views.verify_otp_view, name='verify_otp'),
    
    # User management
    path('api/profile/', views.UserProfileView.as_view(), name='profile'),
    path('api/dashboard/', views.UserDashboardView.as_view(), name='dashboard'),
    
    # Credits & Packages
    path('api/packages/', views.PackageListView.as_view(), name='packages'),
    path('api/purchase-credits/', views.PurchaseCreditsView.as_view(), name='purchase_credits'),
    path('api/check-order-status/', views.check_order_status_view, name='check_order_status'),
    path('api/qpay-webhook/', views.qpay_webhook_view, name='qpay_webhook'),
    
    # Image generation
    path('api/recent-images/', views.RecentImagesView.as_view(), name='recent_images'),
    path('api/generate/', views.GenerateImageView.as_view(), name='generate_image'),
]
