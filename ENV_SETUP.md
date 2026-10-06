# Environment Variables Setup Guide

## Backend (.env file)

Create a `.env` file in the root directory with these variables:

```
DATABASE_URL=postgresql://finuser:Fintrack123@localhost:5432/fintrack
SECRET_KEY=your-secret-key-here-change-this
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=True
ENVIRONMENT=development
ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## Frontend (.env file)

Create a `.env` file in the `frontend/` directory with:

```
VITE_API_BASE_URL=http://localhost:8000
VITE_APP_NAME=Expenzaro
VITE_APP_VERSION=1.0.0
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_NOTIFICATIONS=true
VITE_DEFAULT_CURRENCY=INR
VITE_DEFAULT_LOCALE=en-IN
```

## Important Notes

- **NEVER commit .env files to version control**
- Change the SECRET_KEY to a secure random string
- Adjust database credentials as needed
- Set VITE_API_BASE_URL to your backend URL

## Generate Secret Key

To generate a secure secret key for production:

```bash
python -c \"import secrets; print(secrets.token_urlsafe(32))\"
```