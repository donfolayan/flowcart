<div align="center">

# 🛒 FlowCart

### A Modern, Production-Ready E-Commerce Backend API

[![Python](https://img.shields.io/badge/Python-3.13+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.119+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16+-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://postgresql.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

[Features](#-features) • [Quick Start](#-quick-start) • [API Docs](#-api-documentation) • [Contributing](#-contributing)

</div>

---

## � Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Motivation](#-motivation)
- [Tech Stack](#️-tech-stack)
- [Project Architecture](#-project-architecture)
- [Quick Start](#-quick-start)
- [Configuration](#️-configuration)
- [Database Migrations](#️-database-migrations)
- [API Documentation](#-api-documentation)
- [Authentication Flow](#-authentication-flow)
- [Testing](#-testing)
- [Deployment](#-deployment)
- [Contributing](#-contributing)
- [License](#-license)

---

## �📖 Overview

**FlowCart** is a fully-featured, scalable e-commerce backend API built with modern Python technologies. It provides everything you need to power an online store—from user authentication and product management to shopping carts, payments, and order processing.

Built with **FastAPI** for high performance, **PostgreSQL** for reliable data persistence, and **Stripe** for secure payment processing, FlowCart is designed to be a solid foundation for any e-commerce application.

---

## ✨ Features

<table>
<tr>
<td width="50%">

**🔐 Authentication & Security**
- JWT-based authentication with refresh tokens
- Email verification flow
- Password reset functionality
- Role-based access control (Admin/Customer)
- Rate limiting protection

</td>
<td width="50%">

**🛍️ Product Management**
- Full product CRUD operations
- Product variants (size, color, etc.)
- Category organization
- Media/image management via Cloudinary
- Search and filtering

</td>
</tr>
<tr>
<td width="50%">

**🛒 Shopping Experience**
- Persistent shopping cart
- Guest cart support (session-based)
- Cart to order conversion
- Promo code/discount system

</td>
<td width="50%">

**💳 Orders & Payments**
- Complete order lifecycle management
- Stripe payment integration
- Webhook handling for payment events
- Refund support
- Order history tracking

</td>
</tr>
<tr>
<td width="50%">

**👤 User Management**
- User profiles with customization
- Multiple shipping addresses
- Order history
- Admin dashboard capabilities

</td>
<td width="50%">

**🏗️ Developer Experience**
- Async/await throughout
- Auto-generated OpenAPI docs
- Database migrations with Alembic
- Docker containerization
- Comprehensive test suite

</td>
</tr>
</table>

---

## 💡 Motivation

Building an e-commerce backend from scratch is **hard**. Between authentication, payment processing, inventory management, and order workflows, there's a lot that can go wrong—and a lot of wheels that get reinvented.

**FlowCart exists to change that.**

### The Problem

Most developers face the same challenges when building e-commerce platforms:

- ⏱️ **Time-consuming setup** — Weeks spent on boilerplate before writing business logic
- 🔒 **Security concerns** — Authentication, payment handling, and data protection are complex
- 📈 **Scalability questions** — Will the architecture hold up as the business grows?
- 🧩 **Integration headaches** — Connecting payments, media storage, and email services

### The Solution

FlowCart provides a **production-ready foundation** that handles all the common e-commerce backend requirements out of the box:

| What You Get | Why It Matters |
|--------------|----------------|
| **Battle-tested auth system** | Secure JWT implementation with refresh tokens, email verification, and password reset |
| **Stripe integration** | Payment processing with webhook handling—no need to figure out the flow |
| **Async architecture** | Built for performance from day one with FastAPI and async PostgreSQL |
| **Clean, modular code** | Easy to understand, extend, and customize for your specific needs |
| **Docker-ready** | Deploy anywhere with containerization already configured |

### Who Is This For?

- 🚀 **Startups** wanting to launch quickly without compromising on quality
- 👨‍💻 **Developers** building custom e-commerce solutions for clients
- 📚 **Learners** studying production-grade FastAPI application architecture
- 🏢 **Teams** needing a solid backend foundation to build upon

**FlowCart lets you skip the boring parts and focus on what makes your store unique.**

---

## 🛠️ Tech Stack

FlowCart is built with a carefully selected set of modern, production-proven technologies:

### Core Framework

| Technology | Purpose |
|------------|---------|
| [**FastAPI**](https://fastapi.tiangolo.com) | High-performance async web framework with automatic OpenAPI docs |
| [**Python 3.13+**](https://python.org) | Latest Python with performance improvements and modern syntax |
| [**Pydantic**](https://docs.pydantic.dev) | Data validation and settings management |
| [**Uvicorn**](https://uvicorn.org) | Lightning-fast ASGI server |

### Database & ORM

| Technology | Purpose |
|------------|---------|
| [**PostgreSQL**](https://postgresql.org) | Robust, scalable relational database |
| [**SQLAlchemy 2.0**](https://sqlalchemy.org) | Async ORM with modern Python support |
| [**Alembic**](https://alembic.sqlalchemy.org) | Database migration management |
| [**asyncpg**](https://github.com/MagicStack/asyncpg) | Fast async PostgreSQL driver |

### Authentication & Security

| Technology | Purpose |
|------------|---------|
| [**python-jose**](https://github.com/mpdavis/python-jose) | JWT token creation and validation |
| [**Argon2**](https://argon2-cffi.readthedocs.io) | Secure password hashing (winner of PHC) |
| [**SlowAPI**](https://github.com/laurentS/slowapi) | Rate limiting to prevent abuse |

### External Services

| Technology | Purpose |
|------------|---------|
| [**Stripe**](https://stripe.com) | Payment processing and webhook handling |
| [**Cloudinary**](https://cloudinary.com) | Media/image storage and transformation |
| [**Sentry**](https://sentry.io) | Error tracking and performance monitoring |

### Development & Testing

| Technology | Purpose |
|------------|---------|
| [**pytest**](https://pytest.org) | Testing framework with async support |
| [**pytest-asyncio**](https://github.com/pytest-dev/pytest-asyncio) | Async test support |
| [**pytest-cov**](https://github.com/pytest-dev/pytest-cov) | Code coverage reporting |
| [**Ruff**](https://github.com/astral-sh/ruff) | Fast Python linter and formatter |
| [**pre-commit**](https://pre-commit.com) | Git hooks for code quality |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| [**Docker**](https://docker.com) | Containerization for consistent environments |
| [**Docker Compose**](https://docs.docker.com/compose) | Multi-container orchestration |

### Architecture Highlights

```
┌─────────────────────────────────────────────────────────────────┐
│                         Client Apps                              │
│                  (Web, Mobile, Third-party)                      │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Routes    │  │   Schemas   │  │       Services          │  │
│  │  (API v1)   │──│  (Pydantic) │──│   (Business Logic)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
            ┌───────────────────┼───────────────────┐
            ▼                   ▼                   ▼
    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
    │  PostgreSQL  │    │   Stripe     │    │  Cloudinary  │
    │   Database   │    │  Payments    │    │    Media     │
    └──────────────┘    └──────────────┘    └──────────────┘
```

---

## 📁 Project Architecture

FlowCart follows a **clean, modular architecture** that separates concerns and makes the codebase easy to navigate and extend.

```
flowcart/
├── app/                          # Main application package
│   ├── api/                      # API layer
│   │   ├── dependencies/         # Dependency injection (auth, db sessions)
│   │   ├── routes/               # API route handlers
│   │   │   ├── auth.py           # Authentication endpoints
│   │   │   ├── users.py          # User management
│   │   │   ├── products.py       # Product catalog
│   │   │   ├── categories.py     # Category management
│   │   │   ├── cart.py           # Shopping cart
│   │   │   ├── orders.py         # Order processing
│   │   │   ├── payments.py       # Payment handling
│   │   │   ├── promo_codes.py    # Discount codes
│   │   │   └── ...
│   │   ├── middleware.py         # Custom middleware
│   │   └── exception_handlers.py # Global error handling
│   │
│   ├── core/                     # Core functionality
│   │   ├── config.py             # Application settings
│   │   ├── security.py           # Password hashing, verification
│   │   ├── jwt.py                # JWT token handling
│   │   ├── permissions.py        # Role-based access control
│   │   ├── email/                # Email service providers
│   │   ├── payment/              # Payment provider integrations
│   │   └── storage/              # File storage providers
│   │
│   ├── models/                   # SQLAlchemy/SQLModel database models
│   │   ├── user.py               # User model
│   │   ├── product.py            # Product model
│   │   ├── product_variant.py    # Product variants
│   │   ├── category.py           # Categories
│   │   ├── cart.py               # Shopping cart
│   │   ├── order.py              # Orders
│   │   ├── payment.py            # Payment records
│   │   └── ...
│   │
│   ├── schemas/                  # Pydantic schemas (request/response)
│   │   ├── user.py               # User DTOs
│   │   ├── product.py            # Product DTOs
│   │   ├── auth.py               # Auth DTOs
│   │   └── ...
│   │
│   ├── services/                 # Business logic layer
│   │   ├── cart.py               # Cart operations
│   │   ├── order.py              # Order processing
│   │   ├── order_state.py        # Order state machine
│   │   ├── payment/              # Payment processing
│   │   ├── product.py            # Product operations
│   │   └── promo.py              # Promo code logic
│   │
│   ├── enums/                    # Enumeration types
│   ├── util/                     # Utility functions
│   ├── db/                       # Database utilities
│   ├── tests/                    # Test suite
│   ├── factory.py                # Application factory
│   └── main.py                   # Application entry point
│
├── alembic/                      # Database migrations
│   └── versions/                 # Migration scripts
│
├── logs/                         # Application logs
├── docker-compose.yml            # Docker orchestration
├── Dockerfile                    # Container definition
├── pyproject.toml                # Project dependencies
└── pytest.ini                    # Test configuration
```

### Design Patterns

| Pattern | Implementation |
|---------|----------------|
| **Repository Pattern** | Services abstract database operations from routes |
| **Dependency Injection** | FastAPI's `Depends()` for auth, DB sessions, permissions |
| **Factory Pattern** | `factory.py` creates configured app instances |
| **State Machine** | Order status transitions managed in `order_state.py` |
| **Provider Pattern** | Pluggable payment, storage, and email providers |

---

## 🚀 Quick Start

Get FlowCart running on your machine in minutes.

### Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.13+** — [Download Python](https://python.org/downloads)
- **PostgreSQL 14+** — [Download PostgreSQL](https://postgresql.org/download) or use Docker
- **Docker** (optional) — [Download Docker](https://docker.com/get-started)
- **uv** (recommended) — [Install uv](https://docs.astral.sh/uv/getting-started/installation/)

### Option 1: Docker (Recommended)

The fastest way to get started:

```bash
# Clone the repository
git clone https://github.com/donfolayan/flowcart.git
cd flowcart

# Create environment file
cp .env.example .env
# Edit .env with your configuration (see Configuration section)

# Start with Docker Compose
docker compose up -d

# The API is now running at http://localhost:8000
```

**Development mode with hot reload:**

```bash
docker compose up api-dev
# Available at http://localhost:8001 with auto-reload
```

### Option 2: Local Development

For a traditional local setup:

```bash
# Clone the repository
git clone https://github.com/donfolayan/flowcart.git
cd flowcart

# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Create environment file
cp .env.example .env
# Edit .env with your configuration

# Set up the database
# Make sure PostgreSQL is running, then:
uv run alembic upgrade head

# Start the development server
uv run uvicorn app.main:app --reload

# The API is now running at http://localhost:8000
```

### Option 3: Using pip

If you prefer pip over uv:

```bash
# Clone and enter directory
git clone https://github.com/donfolayan/flowcart.git
cd flowcart

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -e .

# Continue with environment setup and database migration as above
```

### Verify Installation

Once running, verify everything works:

```bash
# Check API health
curl http://localhost:8000/

# View interactive API documentation
open http://localhost:8000/docs
```

You should see the Swagger UI with all available endpoints!

---

## ⚙️ Configuration

FlowCart uses environment variables for configuration. Create a `.env` file in the project root based on the example below.

### Environment Variables

```bash
# ===================
# Server Configuration
# ===================
HOST=0.0.0.0
PORT=8000
RELOAD=false                          # Set to true for development
ENVIRONMENT=development               # development | production

# ===================
# Database
# ===================
DATABASE_URL=postgresql://user:password@localhost:5432/flowcart
ASYNC_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/flowcart
SYNC_DATABASE_URL=postgresql://user:password@localhost:5432/flowcart

# ===================
# Authentication
# ===================
JWT_SECRET_KEY=your-super-secret-key-change-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ===================
# Stripe (Payments)
# ===================
STRIPE_API_KEY=sk_test_xxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx
PAYMENT_PROVIDER=stripe

# ===================
# Cloudinary (Media Storage)
# ===================
CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-api-key
CLOUDINARY_API_SECRET=your-api-secret
STORAGE_PROVIDER=cloudinary
APPLICATION_FOLDER=flowcart_app       # Cloudinary folder for uploads

# ===================
# Email
# ===================
EMAIL_PROVIDER=smtp
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USERNAME=your-email@example.com
EMAIL_PASSWORD=your-email-password
EMAIL_FROM=noreply@yourstore.com
EMAIL_USE_TLS=true
EMAIL_USE_SSL=false
EMAIL_TIMEOUT_SECONDS=10

# ===================
# Business Logic
# ===================
TAX_RATE=0.1                          # 10% tax rate
FRONTEND_URL=http://localhost:3000    # For email links

# ===================
# Monitoring & Logging
# ===================
LOG_LEVEL=INFO                        # DEBUG | INFO | WARNING | ERROR
LOG_FORMAT=console                    # console | json
LOG_DIR=logs
SENTRY_DSN=                           # Optional: Sentry error tracking
SENTRY_TRACES_SAMPLE_RATE=0.1
```

### Configuration by Environment

| Variable | Development | Production |
|----------|-------------|------------|
| `ENVIRONMENT` | `development` | `production` |
| `RELOAD` | `true` | `false` |
| `LOG_LEVEL` | `DEBUG` | `INFO` or `WARNING` |
| `JWT_SECRET_KEY` | Any value | **Strong, unique secret** |
| `STRIPE_API_KEY` | `sk_test_...` | `sk_live_...` |

> ⚠️ **Security Note**: Never commit your `.env` file to version control. The `.gitignore` file already excludes it.

---

## 🗃️ Database Migrations

FlowCart uses **Alembic** for database migrations. All migration files are stored in `alembic/versions/`.

### Running Migrations

```bash
# Apply all pending migrations
uv run alembic upgrade head

# Or with Docker
docker compose exec api alembic upgrade head
```

### Creating New Migrations

When you modify models, create a new migration:

```bash
# Auto-generate migration from model changes
uv run alembic revision --autogenerate -m "description_of_changes"

# Create empty migration for custom SQL
uv run alembic revision -m "description_of_changes"
```

### Common Migration Commands

```bash
# Check current migration status
uv run alembic current

# View migration history
uv run alembic history

# Downgrade one revision
uv run alembic downgrade -1

# Downgrade to specific revision
uv run alembic downgrade <revision_id>

# Downgrade all (reset database)
uv run alembic downgrade base
```

### Migration Best Practices

1. **Always review auto-generated migrations** before applying
2. **Test migrations** on a copy of production data before deploying
3. **Use descriptive names** for migration files
4. **Keep migrations small** — one logical change per migration

---

## 📚 API Documentation

FlowCart provides auto-generated, interactive API documentation.

### Interactive Docs

Once the server is running, access the documentation at:

| URL | Description |
|-----|-------------|
| `http://localhost:8000/docs` | **Swagger UI** — Interactive API explorer |
| `http://localhost:8000/redoc` | **ReDoc** — Alternative documentation view |

### API Endpoints Overview

All endpoints are prefixed with `/api/v1/`.

#### 🔐 Authentication (`/api/v1/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/register` | Create new user account |
| `POST` | `/login` | Authenticate and get tokens |
| `POST` | `/refresh` | Refresh access token |
| `POST` | `/logout` | Invalidate current session |
| `POST` | `/logout-all` | Invalidate all sessions |
| `GET` | `/sessions` | List active sessions |
| `DELETE` | `/sessions/{id}` | Revoke specific session |
| `POST` | `/verify-email` | Verify email with token |
| `POST` | `/resend-verification-email` | Resend verification email |
| `POST` | `/forgot-password` | Request password reset |
| `POST` | `/reset-password` | Reset password with token |

#### 👤 Users (`/api/v1/users`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/me` | Get current user profile |
| `PATCH` | `/me` | Update current user profile |
| `GET` | `/` | List all users (admin) |
| `GET` | `/{id}` | Get user by ID (admin) |

#### 🛍️ Products (`/api/v1/products`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List products (with filters) |
| `GET` | `/{id}` | Get product details |
| `POST` | `/` | Create product (admin) |
| `PATCH` | `/{id}` | Update product (admin) |
| `DELETE` | `/{id}` | Delete product (admin) |

#### 📂 Categories (`/api/v1/categories`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List all categories |
| `GET` | `/{id}` | Get category details |
| `POST` | `/` | Create category (admin) |
| `PATCH` | `/{id}` | Update category (admin) |
| `DELETE` | `/{id}` | Delete category (admin) |

#### 🛒 Cart (`/api/v1/carts`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Get current cart |
| `POST` | `/checkout` | Convert cart to order |

#### 📦 Cart Items (`/api/v1/cart-items`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/` | Add item to cart |
| `PATCH` | `/{id}` | Update item quantity |
| `DELETE` | `/{id}` | Remove item from cart |

#### 📋 Orders (`/api/v1/orders`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List user's orders |
| `GET` | `/{id}` | Get order details |
| `POST` | `/` | Create order from cart |
| `POST` | `/{id}/cancel` | Cancel order |
| `DELETE` | `/{id}` | Delete order (admin) |

#### 💳 Payments (`/api/v1/payments`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/create-intent` | Create payment intent |
| `POST` | `/webhook` | Handle Stripe webhooks |
| `GET` | `/{order_id}` | Get payment status |

#### 🏷️ Promo Codes (`/api/v1/promo-codes`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List promo codes (admin) |
| `POST` | `/` | Create promo code (admin) |
| `POST` | `/validate` | Validate a promo code |
| `PATCH` | `/{id}` | Update promo code (admin) |
| `DELETE` | `/{id}` | Delete promo code (admin) |

#### 📍 Addresses (`/api/v1/addresses`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | List user's addresses |
| `POST` | `/` | Add new address |
| `PATCH` | `/{id}` | Update address |
| `DELETE` | `/{id}` | Delete address |

### Authentication

Most endpoints require authentication via JWT Bearer token:

```bash
# Include in request headers
Authorization: Bearer <your_access_token>
```

**Public endpoints** (no auth required):
- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/products`
- `GET /api/v1/categories`

---

## 🔐 Authentication Flow

FlowCart uses a **JWT-based authentication system** with access and refresh tokens for secure, stateless authentication.

### How It Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Authentication Flow                                │
└─────────────────────────────────────────────────────────────────────────────┘

  ┌──────────┐                                              ┌──────────────┐
  │  Client  │                                              │   FlowCart   │
  └────┬─────┘                                              └──────┬───────┘
       │                                                           │
       │  1. POST /auth/login (email, password)                    │
       │ ─────────────────────────────────────────────────────────>│
       │                                                           │
       │  2. Returns: access_token + refresh_token                 │
       │ <─────────────────────────────────────────────────────────│
       │                                                           │
       │  3. API Request + Authorization: Bearer <access_token>    │
       │ ─────────────────────────────────────────────────────────>│
       │                                                           │
       │  4. Protected resource response                           │
       │ <─────────────────────────────────────────────────────────│
       │                                                           │
       │         ⏰ Access token expires (30 min default)          │
       │                                                           │
       │  5. POST /auth/refresh (refresh_token)                    │
       │ ─────────────────────────────────────────────────────────>│
       │                                                           │
       │  6. New access_token + refresh_token                      │
       │ <─────────────────────────────────────────────────────────│
       │                                                           │
```

### Token Types

| Token | Lifetime | Purpose | Storage Recommendation |
|-------|----------|---------|------------------------|
| **Access Token** | 30 minutes | Authenticate API requests | Memory (JS variable) |
| **Refresh Token** | 7 days | Obtain new access tokens | HttpOnly cookie or secure storage |

### Token Structure

**Access Token Payload:**
```json
{
  "sub": "user-uuid-here",
  "exp": 1699999999
}
```

**Refresh Token Payload:**
```json
{
  "sub": "user-uuid-here",
  "exp": 1700999999,
  "scope": "refresh_token",
  "jti": "token-uuid-for-revocation"
}
```

### Security Features

- ✅ **Password Hashing** — Argon2 (winner of Password Hashing Competition)
- ✅ **Token Revocation** — Refresh tokens tracked in DB for revocation
- ✅ **Session Management** — View and revoke active sessions
- ✅ **Rate Limiting** — Protection against brute force attacks
- ✅ **Email Verification** — Verify user email before full access
- ✅ **Password Reset** — Secure token-based password reset flow

### Example: Login Flow

```bash
# 1. Register a new user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123",
    "first_name": "John",
    "last_name": "Doe"
  }'

# 2. Login to get tokens
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "securepassword123"
  }'

# Response:
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIs...",
#   "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
#   "token_type": "bearer"
# }

# 3. Use access token for authenticated requests
curl http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."

# 4. Refresh when access token expires
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
  }'
```

---

## 🧪 Testing

FlowCart includes a comprehensive test suite using **pytest** with async support.

### Test Structure

```
app/tests/
├── conftest.py              # Shared fixtures
└── unit/                    # Unit tests
    ├── test_api_*.py        # API route tests
    ├── test_services_*.py   # Service layer tests
    ├── test_core_*.py       # Core functionality tests
    └── test_schemas_*.py    # Schema validation tests
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest app/tests/unit/test_jwt.py

# Run tests matching a pattern
uv run pytest -k "test_auth"

# Run with coverage report
uv run pytest --cov=app --cov-report=html

# Run with coverage in terminal
uv run pytest --cov=app --cov-report=term-missing
```

### Test Categories

| Category | Description | Example |
|----------|-------------|---------|
| **API Tests** | Test HTTP endpoints | `test_api_product_routes.py` |
| **Service Tests** | Test business logic | `test_cart_service_unit.py` |
| **Unit Tests** | Test individual functions | `test_jwt.py`, `test_security.py` |
| **Schema Tests** | Test data validation | `test_schema_and_model.py` |

### Writing Tests

Tests use pytest-asyncio for async support:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_product(client: AsyncClient, auth_headers: dict):
    response = await client.post(
        "/api/v1/products",
        json={"name": "Test Product", "price": 29.99},
        headers=auth_headers
    )
    assert response.status_code == 201
    assert response.json()["name"] == "Test Product"
```

### Coverage Goals

We aim for high test coverage on critical paths:
- ✅ Authentication flows
- ✅ Payment processing
- ✅ Order state transitions
- ✅ Cart operations

---

## 🚀 Deployment

FlowCart is designed to be deployed anywhere that supports Docker or Python applications.

### Production Checklist

Before deploying to production, ensure:

- [ ] **Environment variables** are properly set (especially secrets)
- [ ] **`ENVIRONMENT`** is set to `production`
- [ ] **`JWT_SECRET_KEY`** is a strong, unique secret
- [ ] **`STRIPE_API_KEY`** uses live keys (`sk_live_...`)
- [ ] **Database** is properly secured and backed up
- [ ] **HTTPS** is configured (handled automatically in production mode)
- [ ] **Sentry** is configured for error tracking
- [ ] **Rate limiting** is appropriately configured

### Docker Deployment

```bash
# Build production image
docker build -t flowcart:latest .

# Run with environment file
docker run -d \
  --name flowcart \
  -p 8000:8000 \
  --env-file .env.production \
  flowcart:latest
```

### Docker Compose (Production)

```yaml
# docker-compose.prod.yml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env.production
    restart: always
    depends_on:
      - db

  db:
    image: postgres:16-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_USER: flowcart
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: flowcart
    restart: always

volumes:
  postgres_data:
```

### Platform-Specific Guides

<details>
<summary><strong>Railway</strong></summary>

1. Connect your GitHub repository
2. Add environment variables in Railway dashboard
3. Railway auto-detects the Dockerfile
4. Deploy!

</details>

<details>
<summary><strong>Render</strong></summary>

1. Create a new Web Service
2. Connect your repository
3. Set build command: `docker build -t app .`
4. Set start command: `docker run -p 8000:8000 app`
5. Add environment variables
6. Deploy!

</details>

<details>
<summary><strong>DigitalOcean App Platform</strong></summary>

1. Create a new App
2. Select your repository
3. Choose "Dockerfile" as the build type
4. Configure environment variables
5. Deploy!

</details>

<details>
<summary><strong>AWS ECS / Fargate</strong></summary>

1. Push image to ECR
2. Create ECS task definition
3. Configure environment variables from Secrets Manager
4. Create ECS service with desired count
5. Configure load balancer

</details>

### Health Checks

FlowCart exposes a health endpoint for load balancers and orchestrators:

```bash
GET /
# Returns: {"status": "healthy"}
```

---

## 🤝 Contributing

We welcome contributions to FlowCart! Here's how you can help.

### Getting Started

1. **Fork** the repository
2. **Clone** your fork locally
3. **Create a branch** for your feature/fix
4. **Make changes** and add tests
5. **Submit a Pull Request**

### Development Setup

```bash
# Clone your fork
git clone https://github.com/donfolayan/flowcart.git
cd flowcart

# Create virtual environment
uv venv
source .venv/bin/activate

# Install dependencies (including dev)
uv sync

# Install pre-commit hooks
pre-commit install

# Run tests to verify setup
uv run pytest
```

### Code Style

FlowCart uses **Ruff** for linting and formatting:

```bash
# Check for issues
uv run ruff check .

# Fix auto-fixable issues
uv run ruff check . --fix

# Format code
uv run ruff format .
```

### Commit Guidelines

We follow [Conventional Commits](https://conventionalcommits.org):

```
feat: add promo code validation endpoint
fix: correct cart total calculation
docs: update API documentation
test: add tests for order service
refactor: simplify payment processing logic
```

### Pull Request Process

1. **Update documentation** if you change functionality
2. **Add tests** for new features
3. **Ensure all tests pass** (`uv run pytest`)
4. **Ensure code is formatted** (`uv run ruff format .`)
5. **Update the README** if needed
6. **Request review** from maintainers

### Reporting Issues

When reporting issues, please include:
- Python version
- Steps to reproduce
- Expected vs actual behavior
- Error messages and stack traces

---

## 📄 License

FlowCart is open source software licensed under the **MIT License**.

```
MIT License

Copyright (c) 2026 FlowCart Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

<div align="center">

**Built with ❤️ using FastAPI**

[Report Bug](https://github.com/donfolayan/flowcart/issues) • [Request Feature](https://github.com/donfolayan/flowcart/issues) • [Discussions](https://github.com/donfolayan/flowcart/discussions)

</div>
