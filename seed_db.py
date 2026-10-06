# seed_db.py
from datetime import datetime, timedelta
from app.core.database import SessionLocal, Base, engine
from app.core.security import get_password_hash
from app.models.user import User
from app.models.category import Category, CategoryType
from app.models.transaction import Transaction, TransactionType
from app.models.budget import Budget, BudgetPeriod
from app.models.alert import Alert, AlertType, AlertStatus

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Check if user already exists
        user = db.query(User).filter(User.email == "admin@example.com").first()
        if not user:
            print("Creating demo user: admin@example.com...")
            user = User(
                email="admin@example.com",
                full_name="Admin User",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
                role="admin"
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            print("Demo user created.")

        # Seed categories
        existing_categories = {c.name: c for c in db.query(Category).filter(Category.user_id == user.id).all()}
        
        categories_data = [
            ("Salary", CategoryType.income),
            ("Freelance", CategoryType.income),
            ("Investments", CategoryType.income),
            ("Food & Dining", CategoryType.expense),
            ("Rent & Housing", CategoryType.expense),
            ("Transportation", CategoryType.expense),
            ("Entertainment", CategoryType.expense),
            ("Utilities", CategoryType.expense),
            ("Shopping", CategoryType.expense),
        ]

        created_cats = {}
        for name, c_type in categories_data:
            if name not in existing_categories:
                cat = Category(name=name, type=c_type, user_id=user.id)
                db.add(cat)
                db.commit()
                db.refresh(cat)
                created_cats[name] = cat
            else:
                created_cats[name] = existing_categories[name]

        # Seed sample budgets if none exist
        budget_count = db.query(Budget).filter(Budget.user_id == user.id).count()
        if budget_count == 0 and "Food & Dining" in created_cats:
            start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
            
            b1 = Budget(
                user_id=user.id,
                category_id=created_cats["Food & Dining"].id,
                name="Monthly Food Budget",
                limit_amount=15000.0,
                period=BudgetPeriod.monthly,
                start_date=start_of_month,
                end_date=end_of_month,
                is_active=True,
                alert_threshold=80.0
            )
            db.add(b1)
            
            if "Transportation" in created_cats:
                b2 = Budget(
                    user_id=user.id,
                    category_id=created_cats["Transportation"].id,
                    name="Transportation Budget",
                    limit_amount=6000.0,
                    period=BudgetPeriod.monthly,
                    start_date=start_of_month,
                    end_date=end_of_month,
                    is_active=True,
                    alert_threshold=80.0
                )
                db.add(b2)
            db.commit()

        # Seed sample transactions if none exist
        tx_count = db.query(Transaction).filter(Transaction.user_id == user.id).count()
        if tx_count == 0:
            now = datetime.utcnow()
            transactions_data = [
                (now - timedelta(days=5), 85000.0, "Monthly Salary", "Tech Corp", TransactionType.income, "Salary"),
                (now - timedelta(days=4), 25000.0, "Apartment Rent", "Landlord", TransactionType.expense, "Rent & Housing"),
                (now - timedelta(days=3), 3200.0, "Supermarket Groceries", "Nature Basket", TransactionType.expense, "Food & Dining"),
                (now - timedelta(days=2), 1450.0, "Dinner with friends", "Bistro Cafe", TransactionType.expense, "Food & Dining"),
                (now - timedelta(days=2), 2200.0, "Petrol / Fuel", "Shell Fuel Station", TransactionType.expense, "Transportation"),
                (now - timedelta(days=1), 12000.0, "Freelance Design UI", "Acme Client", TransactionType.income, "Freelance"),
                (now - timedelta(days=1), 899.0, "Electricity Bill", "State Power Board", TransactionType.expense, "Utilities"),
                (now, 450.0, "Coffee & Snacks", "Blue Tokai", TransactionType.expense, "Food & Dining"),
            ]

            for dt, amt, desc, merch, ttype, cname in transactions_data:
                cat = created_cats.get(cname)
                t = Transaction(
                    user_id=user.id,
                    category_id=cat.id if cat else None,
                    date=dt,
                    amount=amt,
                    description=desc,
                    merchant=merch,
                    transaction_type=ttype,
                    notes="Sample demo transaction"
                )
                db.add(t)
            db.commit()

        # Seed welcome alert
        alert_count = db.query(Alert).filter(Alert.user_id == user.id).count()
        if alert_count == 0:
            welcome_alert = Alert(
                user_id=user.id,
                title="Welcome to Expenzaro!",
                message="Your personal finance dashboard has been set up with sample data to explore.",
                alert_type=AlertType.monthly_summary,
                status=AlertStatus.unread,
                priority="low"
            )
            db.add(welcome_alert)
            db.commit()

        print("Database seeded successfully!")
    finally:
        db.close()

if __name__ == "__main__":
    seed()
