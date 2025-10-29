from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


def landing_view(request):
    """Landing page for marketing and conversion"""
    return render(request, 'landing.html')


def index_view(request):
    """Home page with upload form for authenticated users"""
    if not request.user.is_authenticated:
        return redirect('/')
    return render(request, 'index.html', {'user': request.user})


def login_page(request):
    """Login page - redirect to landing page with login modal"""
    return redirect('/#login')


def signup_page(request):
    """Signup page - redirect to landing page with signup modal"""
    return redirect('/#signup')


@login_required
def dashboard_view(request):
    """User dashboard"""
    return render(request, 'dashboard.html')
