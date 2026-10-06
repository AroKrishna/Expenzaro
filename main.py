# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from app.api.v1.endpoints import user,auth,category,transaction,budget,alert,dashboard,forecasting,anomaly
from app.core.database import Base, engine
from app.models import user as user_model  # ensure User table is known
from app.models import category as category_model
from app.models import transaction as transaction_model
from app.models import budget as budget_model
from app.models import alert as alert_model

app = FastAPI(
    title="Expenzaro API",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# main.py (add this near app creation)
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

# include routers
app.include_router(user.router, prefix="/users", tags=["Users"])
app.include_router(auth.router)  # <--- add this
app.include_router(category.router, prefix="/categories", tags=["Categories"])
app.include_router(transaction.router, prefix="/transactions", tags=["Transactions"])
app.include_router(budget.router, prefix="/budgets", tags=["Budgets"])
app.include_router(alert.router, prefix="/alerts", tags=["Alerts"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(forecasting.router, prefix="/forecasting", tags=["Forecasting"])
app.include_router(anomaly.router, prefix="/anomaly", tags=["Anomaly Detection"])

@app.get("/")
def read_root():
    return {"message": "Welcome to Expenzaro API"}


# ✅ Custom OpenAPI schema with JWT Bearer
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description="Expenzaro API with JWT Authentication",
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    for path in openapi_schema["paths"].values():
        for method in path.values():
            method.setdefault("security", [{"BearerAuth": []}])
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi    
