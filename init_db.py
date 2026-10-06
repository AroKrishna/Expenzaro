# init_db.py
from app.core.database import Base, engine
from app.models import user, category, transaction, budget, alert   # import all models

print("Creating tables...")
Base.metadata.create_all(bind=engine)
print("Tables created successfully!")
