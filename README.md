# ReGer AI - AI Interior Design Generator

A web application where users can upload photos of their rooms and generate new interior design renders using AI (DALL·E 3). The system displays before-and-after comparison images side by side with an interactive slider.

## 🚀 Features

- **Landing Page**: Modern, conversion-focused marketing page with features and testimonials
- **User Authentication**: Sign up, login, and user management
- **Credit System**: Each user starts with 3 free credits, with option to purchase more
- **AI Image Generation**: Upload room photos and generate new designs using DALL·E 3
- **Style Selection**: Choose from 8 different interior design styles
- **Before-After Comparison**: Interactive slider to compare original and generated images
- **Dashboard**: View credit balance, transaction history, and generated designs
- **Responsive Design**: Beautiful UI built with Tailwind CSS

## 🛠 Tech Stack

- **Backend**: Django 4.2.7 + Django REST Framework
- **Frontend**: Tailwind CSS + HTML templates
- **AI Integration**: OpenAI DALL·E 3 API
- **Database**: SQLite (easily switchable to PostgreSQL)
- **Authentication**: Django's built-in user system

## 📦 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd rehome
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp env.example .env
   ```
   
   Edit `.env` and add your OpenAI API key:
   ```
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   OPENAI_API_KEY=your-openai-api-key-here
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser (optional)**
   ```bash
   python manage.py createsuperuser
   ```

6. **Seed test data (optional)**
   ```bash
   python manage.py seed_data
   ```

7. **Start the development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - Landing page: http://127.0.0.1:8000/
   - Main app: http://127.0.0.1:8000/app/
   - Admin panel: http://127.0.0.1:8000/admin/

## 🎯 Usage

### Getting Started

1. **Sign Up**: Create a new account to get 3 free credits
2. **Upload**: Upload a photo of your room
3. **Choose Style**: Select from 8 different design styles:
   - Modern
   - Minimal
   - Luxury
   - Rustic
   - Industrial
   - Scandinavian
   - Bohemian
   - Traditional
4. **Generate**: Click "Generate Design" to create your AI-powered redesign
5. **Compare**: Use the interactive slider to compare before and after images

### Credit System

- **Free Credits**: New users receive 3 free credits upon signup
- **Credit Usage**: Each image generation costs 1 credit
- **Purchase Credits**: Buy 10 credits for 5,000 MNT (simulated payment)
- **Dashboard**: Monitor your credit balance and usage history

### Test Accounts

The seed script creates these test accounts:
- Username: `demo`, Password: `demo123`
- Username: `testuser`, Password: `test123`

## 🔧 API Endpoints

### Authentication
- `POST /api/login/` - User login
- `POST /api/logout/` - User logout
- `POST /api/signup/` - User registration

### User Management
- `GET /api/profile/` - Get user profile
- `GET /api/dashboard/` - Get dashboard data (credits, images, transactions)

### Credits
- `POST /api/purchase-credits/` - Purchase credits (simulated)

### Image Generation
- `POST /api/generate/` - Generate new room design

## 📁 Project Structure

```
rehome/
├── core/                    # Main Django app
│   ├── models.py           # Database models
│   ├── views.py            # API views
│   ├── views_frontend.py   # Frontend views
│   ├── serializers.py      # API serializers
│   ├── urls.py             # URL routing
│   └── admin.py            # Admin configuration
├── templates/              # HTML templates
│   ├── base.html          # Base template
│   ├── index.html         # Home page
│   ├── login.html         # Login page
│   ├── signup.html        # Signup page
│   └── dashboard.html     # User dashboard
├── static/                # Static files (CSS, JS)
├── media/                 # Uploaded files
├── rehome_project/        # Django project settings
└── manage.py             # Django management script
```

## 🎨 Design Styles

The application supports 8 different interior design styles:

1. **Modern**: Clean lines, neutral colors, minimalist furniture
2. **Minimal**: Ultra-clean, uncluttered spaces with essential elements only
3. **Luxury**: High-end materials, elegant furniture, sophisticated lighting
4. **Rustic**: Natural materials, warm colors, cozy atmosphere
5. **Industrial**: Exposed brick, metal accents, urban loft aesthetic
6. **Scandinavian**: Light colors, natural wood, hygge-inspired comfort
7. **Bohemian**: Eclectic mix, vibrant colors, artistic elements
8. **Traditional**: Classic furniture, rich colors, timeless elegance

## 🔐 Security Features

- CSRF protection enabled
- User authentication required for protected endpoints
- File upload validation
- Credit balance validation before image generation

## 🚀 Deployment

For production deployment:

1. Set `DEBUG=False` in your environment variables
2. Configure a production database (PostgreSQL recommended)
3. Set up static file serving (AWS S3, etc.)
4. Configure proper CORS settings
5. Use a production WSGI server (Gunicorn)
6. Set up proper logging and monitoring

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For support and questions, please open an issue in the repository.
