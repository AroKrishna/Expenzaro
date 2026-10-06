# Expenzaro - Personal Finance Management System

**A modern personal finance management application with transaction tracking, budgeting, and financial insights**

## Features

### 💰 Transaction Management
- Record and categorize income and expenses
- Smart transaction categorization
- Real-time transaction tracking
- Search and filter capabilities

### 📊 Budget Management
- Create monthly, weekly budgets
- Visual budget progress tracking
- Budget alerts and notifications
- Category-based spending limits

### 🔔 Smart Alerts
- Budget limit notifications
- Unusual spending detection
- Monthly financial reports
- Customizable alert preferences

### 📈 Financial Analytics
- Spending pattern analysis
- Category-wise expense breakdown
- Income vs expense trends
- Financial health insights

### 🌍 Localization
- Indian Rupee (INR) currency support
- Indian number formatting (1,23,45,678.90)
- Regional date formats (DD/MM/YYYY)
- Multi-language support

## Technology Stack

**Backend:**
- Python 3.10+ with FastAPI
- PostgreSQL database
- SQLAlchemy ORM
- JWT authentication
- Alembic migrations

**Frontend:**
- React 18+ with TypeScript
- Vite build tool
- Tailwind CSS styling
- TanStack Query for state management
- Chart.js for data visualization

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL 13+

### Backend Setup

1. **Setup environment**
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure database**
```bash
# Create PostgreSQL database
sudo -u postgres psql
CREATE DATABASE fintrack;
CREATE USER finuser WITH PASSWORD 'Fintrack123';
GRANT ALL PRIVILEGES ON DATABASE fintrack TO finuser;
\q
```

3. **Setup environment variables**
```bash
# Create .env file with your own values
DATABASE_URL=postgresql://finuser:Fintrack123@localhost:5432/fintrack
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

4. **Initialize database and start server**
```bash
python init_db.py
alembic upgrade head
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup

1. **Install dependencies**
```bash
cd frontend
npm install
```

2. **Configure environment**
```bash
# Create .env file with your own values
VITE_API_BASE_URL=http://localhost:8000
```

3. **Start development server**
```bash
npm run dev
```

### Access Application
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

### Default Login
```
Email: admin@example.com
Password: admin123
```

## Project Structure

```
fintrack2/
├── app/                    # Backend application
│   ├── api/               # REST API endpoints
│   ├── core/              # Core configuration
│   ├── crud/              # Database operations
│   ├── models/            # Database models
│   ├── schemas/           # Data validation
│   └── services/          # Business logic
├── frontend/              # React frontend
│   └── src/
│       ├── components/    # UI components
│       ├── pages/         # Page components
│       ├── contexts/      # React contexts
│       └── lib/           # API client
├── tests/                 # Backend tests
├── alembic/               # Database migrations
└── requirements.txt       # Python dependencies
```

## API Endpoints

### Authentication
- `POST /auth/login` - User login
- `GET /users/me` - Current user profile

### Transactions
- `GET /transactions/` - List transactions
- `POST /transactions/` - Create transaction
- `PUT /transactions/{id}` - Update transaction
- `DELETE /transactions/{id}` - Delete transaction

### Budgets
- `GET /budgets/` - List budgets
- `POST /budgets/` - Create budget
- `PUT /budgets/{id}` - Update budget
- `DELETE /budgets/{id}` - Delete budget

### Categories
- `GET /categories/` - List categories
- `POST /categories/` - Create category
- `PUT /categories/{id}` - Update category
- `DELETE /categories/{id}` - Delete category

## Testing

### Backend
```bash
pytest
pytest --cov=app  # With coverage
```

### Frontend
```bash
cd frontend
npm run test
npm run build  # Production build
```

## Production Deployment

### Backend
```bash
# Set production environment
export DATABASE_URL=postgresql://user:password@localhost:5432/fintrack_prod
export SECRET_KEY=production-secret-key

# Run migrations
alembic upgrade head

# Start with Gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000
```

### Frontend
```bash
cd frontend
npm run build
# Deploy 'dist' folder to web server
```

