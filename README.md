# GrooveStore API

A Django REST API for an e-commerce platform built as part of the Savannah Informatics backend engineering assessment.

## Table of Contents

- [Features](#features)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [API Usage](#api-usage)
- [Authentication](#authentication)
- [Testing](#testing)
- [Deployment](#deployment)
- [CI/CD](#cicd)
- [API Documentation](#api-documentation)

## Features

✅ **Core Models**: Customer, Category (hierarchical), Product, Order
✅ **REST API**: Full CRUD operations with Django REST Framework
✅ **Hierarchical Categories**: Arbitrary-depth category nesting
✅ **Average Price Calculation**: Recursive calculation for categories and subcategories
✅ **Order Management**: Complete order placement with inventory tracking
✅ **Authentication**: OpenID Connect integration (demo mode included)
✅ **Notifications**: SMS (Africa's Talking) and Email notifications
✅ **Testing**: Comprehensive unit tests with coverage
✅ **CI/CD**: GitHub Actions pipeline
✅ **Containerization**: Docker support
✅ **Kubernetes**: Production-ready K8s manifests

## Tech Stack

- **Backend**: Django 4.2, Django REST Framework 3.14
- **Database**: SQLite (development), PostgreSQL (production ready)
- **Authentication**: JWT tokens, OpenID Connect
- **Testing**: pytest, pytest-django, coverage
- **SMS**: Africa's Talking API
- **Email**: Django email backend (SMTP)
- **Containerization**: Docker, Docker Compose
- **Orchestration**: Kubernetes
- **CI/CD**: GitHub Actions

## Project Structure

```
groovestore_api/
├── groovestore_api/            # Django project
│   ├── groovestore_api/        # Settings and configuration
│   ├── api/                    # Main API application
│   │   ├── models.py          # Database models
│   │   ├── serializers.py     # DRF serializers
│   │   ├── views.py           # API views
│   │   ├── urls.py            # URL routing
│   │   ├── auth.py            # OIDC authentication
│   │   ├── admin.py           # Django admin
│   │   └── tests.py           # Unit tests
│   ├── manage.py              # Django management
│   ├── requirements.txt       # Python dependencies
│   └── pytest.ini            # Test configuration
├── k8s/                       # Kubernetes manifests
├── .github/workflows/         # GitHub Actions
├── Dockerfile                 # Container definition
├── docker-compose.yml         # Development setup
└── README.md                  # This file
```

## Setup Instructions

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd groovestore_api
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   cd groovestore_api
   pip install -r requirements.txt
   ```

4. **Set up environment variables** (optional)
   ```bash
   # Create .env file in groovestore_api/ directory
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   
   # SMS Configuration
   AFRICAS_TALKING_USERNAME=sandbox
   AFRICAS_TALKING_API_KEY=your-api-key
   
   # Email Configuration
   EMAIL_HOST=smtp.gmail.com
   EMAIL_PORT=587
   EMAIL_USE_TLS=True
   EMAIL_HOST_USER=your-email@gmail.com
   EMAIL_HOST_PASSWORD=your-app-password
   DEFAULT_FROM_EMAIL=noreply@groovestore.com
   
   # OIDC Configuration (optional)
   OIDC_ISSUER=https://your-oidc-provider.com
   OIDC_CLIENT_ID=your-client-id
   OIDC_CLIENT_SECRET=your-client-secret
   ```

5. **Run migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

7. **Start development server**
   ```bash
   python manage.py runserver
   ```

8. **Access the application**
   - API: http://localhost:8000/api/v1/
   - Admin: http://localhost:8000/admin/

### Docker Development

1. **Using Docker Compose**
   ```bash
   docker-compose up --build
   ```

2. **Run migrations in container**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

3. **Create superuser in container**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

## API Usage

### Base URL
```
http://localhost:8000/api/v1/
```

### Authentication Endpoints
```bash
# Get OIDC configuration
GET /auth/oidc/config/

# Demo authentication (for testing)
POST /auth/oidc/
{
  "user_info": {
    "email": "user@example.com",
    "name": "Test User",
    "phone": "+1234567890"
  }
}

# JWT token authentication
POST /auth/token/
{
  "username": "your-username",
  "password": "your-password"
}
```

### Category Endpoints
```bash
# List root categories
GET /categories/

# List all categories
GET /categories/all/

# Create category
POST /categories/
{
  "name": "Electronics",
  "description": "Electronic products",
  "parent": null
}

# Get category average price (including subcategories)
GET /categories/{id}/average-price/
```

### Product Endpoints
```bash
# List products
GET /products/

# Create product with nested categories
POST /products/
{
  "name": "Gaming Laptop",
  "description": "High-performance gaming laptop",
  "price": "1599.99",
  "category_path": ["Electronics", "Computers", "Gaming Laptops"],
  "sku": "GAMING001",
  "stock_quantity": 10
}

# Bulk upload products
POST /products/bulk-upload/
[
  {
    "name": "Product 1",
    "price": "99.99",
    "category_path": ["Category", "Subcategory"],
    "sku": "PROD001",
    "stock_quantity": 50
  }
]
```

### Order Endpoints
```bash
# Create order
POST /orders/
{
  "customer": 1,
  "notes": "Rush delivery",
  "items": [
    {"product_id": "1", "quantity": "2"},
    {"product_id": "2", "quantity": "1"}
  ]
}

# List user's orders
GET /orders/
```

### Example Category Hierarchy

The API supports arbitrary-depth category hierarchies. Example:

```
All Products
├── Bakery
│   ├── Bread
│   └── Cookies
└── Produce
    ├── Fruits
    │   ├── Apples
    │   └── Bananas
    └── Vegetables
        └── Carrots
```

## Authentication

### OpenID Connect (Production)

1. **Configure OIDC Provider**
   - Set `OIDC_ISSUER`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET` in settings
   - Configure redirect URI: `{your-domain}/api/v1/auth/oidc/callback/`

2. **Integration Flow**
   - Frontend redirects to OIDC provider
   - User authenticates
   - Provider redirects to callback with code
   - Exchange code for tokens
   - Create/update user and customer profile

### Demo Mode (Development/Testing)

For testing without OIDC provider:

```bash
POST /api/v1/auth/oidc/
{
  "user_info": {
    "email": "demo@example.com",
    "name": "Demo User",
    "phone": "+1234567890"
  }
}
```

Response includes JWT tokens for API access.

## Testing

### Run Tests
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=api --cov-report=html

# Run specific test
python -m pytest api/tests.py::ModelTestCase::test_category_hierarchy
```

### Test Coverage
Current coverage: 80%+ across all modules

### Test Categories
- **Model Tests**: Database model functionality
- **API Tests**: REST endpoint testing
- **Authentication Tests**: OIDC integration
- **Business Logic Tests**: Category hierarchy, order calculations

## Deployment

### Docker

1. **Build image**
   ```bash
   docker build -t groovestore-api .
   ```

2. **Run container**
   ```bash
   docker run -p 8000:8000 groovestore-api
   ```

### Kubernetes

1. **Prerequisites**
   - Kubernetes cluster (minikube, kind, or cloud provider)
   - kubectl configured
   - Ingress controller (optional)

2. **Deploy**
   ```bash
   cd k8s
   chmod +x deploy.sh
   ./deploy.sh
   ```

3. **Access application**
   ```bash
   # Port forward
   kubectl port-forward -n groovestore service/groovestore-api-service 8080:80
   
   # Or use NodePort
   # http://localhost:30080
   ```

4. **Update secrets**
   ```bash
   kubectl create secret generic groovestore-secrets \
     --from-literal=SECRET_KEY=your-secret-key \
     --from-literal=AFRICAS_TALKING_API_KEY=your-api-key \
     --namespace=groovestore
   ```

## CI/CD

### GitHub Actions Pipeline

The project includes a comprehensive CI/CD pipeline:

1. **Test Stage**
   - Multi-Python version testing (3.9, 3.10, 3.11)
   - Unit tests with coverage reporting
   - Coverage uploaded to Codecov

2. **Lint Stage**
   - Code formatting with Black
   - Import sorting with isort
   - Linting with flake8

3. **Security Stage**
   - Security scanning with Bandit
   - Dependency vulnerability checking with Safety

4. **Build & Deploy Stage** (on main branch)
   - Docker image build and push
   - Automated deployment (configurable)

### Configuration

Set up the following GitHub secrets:
- `DOCKERHUB_USERNAME`: Docker Hub username
- `DOCKERHUB_TOKEN`: Docker Hub access token

## API Documentation

### Core Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/oidc/` | POST | OIDC authentication |
| `/auth/token/` | POST | JWT token authentication |
| `/categories/` | GET, POST | Root categories |
| `/categories/all/` | GET | All categories |
| `/categories/{id}/average-price/` | GET | Category price analysis |
| `/products/` | GET, POST | Product management |
| `/products/bulk-upload/` | POST | Bulk product upload |
| `/orders/` | GET, POST | Order management |
| `/customers/` | GET, POST | Customer management |

### Response Format

All API responses follow this format:

```json
{
  "results": [...],           // For list endpoints
  "count": 100,              // Total count
  "next": "...",             // Next page URL
  "previous": "..."          // Previous page URL
}
```

### Error Handling

```json
{
  "error": "Error message",
  "details": {...}           // Additional error details
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Ensure CI passes
5. Submit a pull request

## License

This project is part of a technical assessment for Savannah Informatics.

## Support

For questions or issues, please create an issue in the repository.
