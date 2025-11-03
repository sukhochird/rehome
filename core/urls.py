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
    
    # API endpoints
    path('api/login/', views.login_view, name='login'),
    path('api/logout/', views.logout_view, name='logout'),
    path('api/signup/', views.signup_view, name='signup'),
    
    # User management
    path('api/profile/', views.UserProfileView.as_view(), name='profile'),
    path('api/dashboard/', views.UserDashboardView.as_view(), name='dashboard'),
    
    # Credits
    path('api/purchase-credits/', views.PurchaseCreditsView.as_view(), name='purchase_credits'),
    
    # Image generation
    path('api/recent-images/', views.RecentImagesView.as_view(), name='recent_images'),
    path('api/generate/', views.GenerateImageView.as_view(), name='generate_image'),
]
