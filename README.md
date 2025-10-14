# ChatDys Backend API

Complete backend API for ChatDys - AI Assistant for Dysautonomia and Long Covid.

## 🚀 Features

### ✅ Authentication & Authorization
- **Auth0 Integration** - Complete JWT token validation
- **User Management** - Automatic user creation and profile management
- **Session Tracking** - Login counts, timestamps, and activity monitoring

### ✅ Chat Functionality
- **OpenAI Integration** - GPT-4 powered responses specialized for dysautonomia/POTS/Long Covid
- **Conversation History** - Full conversation tracking (premium feature)
- **Usage Limits** - Free users: 5 questions/day, Premium: unlimited
- **Smart Responses** - Fallback responses when OpenAI is unavailable

### ✅ Premium Subscriptions
- **Stripe Integration** - Complete payment processing
- **Subscription Management** - Customer portal, webhooks, status tracking
- **Feature Gating** - Premium-only features like conversation history

### ✅ User Profiles
- **Profile Completion** - Onboarding flow with health information
- **Preferences** - User settings and notification preferences
- **Health Tracking** - Conditions, symptoms, medications storage

### ✅ Database Management
- **SQLAlchemy ORM** - Full database abstraction
- **SQLite Development** - Easy local development
- **PostgreSQL Ready** - Production database support
- **Migrations** - Database schema versioning

## 📁 Project Structure

```
chatdys-backend/
├── api/                    # API route handlers
│   ├── auth_routes.py     # Authentication endpoints
│   ├── chat_routes.py     # Chat and conversation endpoints
│   ├── payment_routes.py  # Stripe payment endpoints
│   └── user_routes.py     # User management endpoints
├── auth/                   # Authentication logic
│   └── auth0_manager.py   # Auth0 token validation
├── chat/                   # Chat functionality
│   └── chat_service.py    # OpenAI integration and responses
├── config/                 # Configuration
│   └── settings.py        # Application settings
├── database/               # Database management
│   └── connection.py      # Database connection and session management
├── models/                 # Database models
│   ├── conversation.py    # Conversation and Message models
│   └── user.py           # User model
├── payments/               # Payment processing
│   └── stripe_service.py  # Stripe integration
├── utils/                  # Utilities (empty, ready for expansion)
├── app.py                 # Main FastAPI application
├── requirements.txt       # Python dependencies
├── .env                   # Environment variables (template)
├── .env.example          # Environment variables example
└── README.md             # This file
```

## 🛠️ Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env` and update with your actual values:

```bash
cp .env.example .env
```

**Required Configuration:**
- `AUTH0_DOMAIN` - Your Auth0 domain
- `AUTH0_CLIENT_ID` - Your Auth0 application client ID
- `AUTH0_CLIENT_SECRET` - Your Auth0 application client secret
- `AUTH0_AUDIENCE` - Your Auth0 API audience
- `OPENAI_API_KEY` - Your OpenAI API key

**Optional Configuration:**
- `STRIPE_SECRET_KEY` - For payment processing
- `HUBSPOT_ACCESS_TOKEN` - For CRM integration
- `DATABASE_URL` - For PostgreSQL (defaults to SQLite)

### 3. Run the Application

```bash
# Development mode
uvicorn app:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### 4. API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation (Swagger UI)

## 🔗 API Endpoints

### Authentication
- `POST /auth/validate-token` - Validate Auth0 token
- `GET /auth/user-info` - Get authenticated user info
- `GET /auth/check-auth` - Check authentication status

### User Management
- `GET /api/user/session` - Get user session data
- `GET /api/user/profile` - Get detailed user profile
- `POST /api/user/increment-question` - Increment question count
- `POST /api/user/complete-profile` - Complete user profile
- `PUT /api/user/preferences` - Update user preferences
- `GET /api/user/usage` - Get usage statistics

### Chat
- `POST /api/query` - Send chat message and get AI response
- `GET /api/conversations` - Get conversation history (premium)
- `GET /api/conversations/{id}` - Get specific conversation
- `DELETE /api/conversations/{id}` - Delete conversation
- `PUT /api/conversations/{id}/title` - Update conversation title

### Payments
- `POST /api/payments/create-checkout-session` - Create Stripe checkout
- `POST /api/payments/create-portal-session` - Create customer portal
- `POST /api/payments/webhook` - Handle Stripe webhooks
- `GET /api/payments/subscription-status` - Get subscription status

## 🗄️ Database Schema

### Users Table
- Basic profile information (name, email, picture)
- Authentication data (Auth0 sub, login tracking)
- Health information (age, conditions, symptoms, medications)
- Usage tracking (question counts, conversation counts)
- Premium subscription data
- Preferences and settings

### Conversations Table
- User relationship
- Conversation metadata (title, summary)
- Message count and timestamps

### Messages Table
- Conversation relationship
- Role (user/assistant) and content
- AI metadata (model used, token count, sources)
- Processing information

## 🔧 Configuration Options

### Rate Limiting
- `FREE_USER_DAILY_LIMIT` - Questions per day for free users (default: 5)
- `PREMIUM_USER_DAILY_LIMIT` - Questions per day for premium users (default: 1000)

### OpenAI Settings
- Model: GPT-4 (configurable)
- Max tokens: 1000
- Temperature: 0.7
- Specialized system prompt for dysautonomia/POTS/Long Covid

### Database
- Development: SQLite (automatic setup)
- Production: PostgreSQL (configure DATABASE_URL)

## 🚀 Deployment

### Environment Variables for Production
```bash
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql://user:password@host:port/database
```

### Docker Deployment (Optional)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Health Checks
- `GET /` - Basic API info
- `GET /health` - Health check endpoint

## 🔒 Security Features

- **JWT Token Validation** - All endpoints require valid Auth0 tokens
- **CORS Configuration** - Properly configured for frontend domains
- **Input Validation** - Pydantic models for request validation
- **SQL Injection Protection** - SQLAlchemy ORM prevents SQL injection
- **Rate Limiting** - Built-in usage limits for free users

## 📊 Monitoring & Logging

- **Structured Logging** - All important events logged
- **Error Handling** - Comprehensive error handling and reporting
- **Database Monitoring** - Connection pooling and health checks

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=.
```

## 🤝 Integration with Frontend

The backend is designed to work seamlessly with the frontend authentication files:

1. **Frontend** handles Auth0 login/logout
2. **Frontend** sends JWT tokens with API requests
3. **Backend** validates tokens and manages user sessions
4. **Backend** provides all data and functionality via REST API

## 📝 Notes

- **Fallback Responses** - Chat service provides helpful responses even when OpenAI is unavailable
- **Graceful Degradation** - All features work with or without optional services (Stripe, HubSpot)
- **Development Friendly** - SQLite database for easy local development
- **Production Ready** - Comprehensive error handling and logging

## 🆘 Troubleshooting

### Common Issues

1. **Auth0 Token Validation Fails**
   - Check AUTH0_DOMAIN and AUTH0_AUDIENCE settings
   - Ensure token is being sent in Authorization header

2. **Database Connection Issues**
   - For SQLite: Ensure write permissions in app directory
   - For PostgreSQL: Check DATABASE_URL format and connectivity

3. **OpenAI API Errors**
   - Verify OPENAI_API_KEY is set correctly
   - Check API quota and billing status

4. **Stripe Webhook Issues**
   - Ensure STRIPE_WEBHOOK_SECRET matches Stripe dashboard
   - Check webhook endpoint URL in Stripe settings

For more help, check the logs or create an issue in the repository.
#   U p d a t e d   f o r   R a i l w a y   C O R S   f i x  
 