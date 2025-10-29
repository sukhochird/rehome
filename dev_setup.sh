#!/bin/bash

# Development setup script for ReHome

echo "🏠 Setting up ReHome development environment..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Run migrations
echo "🗄️ Running database migrations..."
python manage.py migrate

# Create superuser if it doesn't exist
echo "👤 Creating superuser..."
echo "from django.contrib.auth.models import User; User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'admin123')" | python manage.py shell

# Seed test data
echo "🌱 Seeding test data..."
python manage.py seed_data

# Create media directories
echo "📁 Creating media directories..."
mkdir -p media/original_images media/generated_images

echo "✅ Setup complete!"
echo ""
echo "🚀 To start the development server:"
echo "   python manage.py runserver"
echo ""
echo "🔑 Admin credentials:"
echo "   Username: admin"
echo "   Password: admin123"
echo ""
echo "👥 Test user accounts:"
echo "   Username: demo, Password: demo123"
echo "   Username: testuser, Password: test123"
echo ""
echo "⚠️  Don't forget to set your OPENAI_API_KEY in the .env file!"
