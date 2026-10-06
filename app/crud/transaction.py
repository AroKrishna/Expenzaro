# app/crud/transaction.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, func, desc, asc, extract
from decimal import Decimal

from app.models.transaction import Transaction, TransactionType
from app.models.category import Category
from app.schemas.transaction import TransactionCreate, TransactionUpdate, TransactionFilter, TransactionSummary

def create_transaction(db: Session, transaction: TransactionCreate, user_id: int) -> Transaction:
    """Create a new transaction"""
    db_transaction = Transaction(
        user_id=user_id,
        **transaction.dict()
    )
    db.add(db_transaction)
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def get_transaction(db: Session, transaction_id: int, user_id: int) -> Optional[Transaction]:
    """Get a specific transaction by ID"""
    return db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id
    ).options(joinedload(Transaction.category)).first()

def get_transactions(
    db: Session, 
    user_id: int, 
    skip: int = 0, 
    limit: int = 100,
    filters: Optional[TransactionFilter] = None,
    sort_by: str = "date",
    sort_order: str = "desc"
) -> List[Transaction]:
    """Get transactions with filtering and pagination"""
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    
    # Apply filters
    if filters:
        if filters.start_date:
            query = query.filter(Transaction.date >= filters.start_date)
        if filters.end_date:
            query = query.filter(Transaction.date <= filters.end_date)
        if filters.category_id:
            query = query.filter(Transaction.category_id == filters.category_id)
        if filters.transaction_type:
            query = query.filter(Transaction.transaction_type == filters.transaction_type)
        if filters.min_amount:
            query = query.filter(Transaction.amount >= filters.min_amount)
        if filters.max_amount:
            query = query.filter(Transaction.amount <= filters.max_amount)
        if filters.merchant:
            query = query.filter(Transaction.merchant.ilike(f"%{filters.merchant}%"))
        if filters.description_search:
            query = query.filter(
                or_(
                    Transaction.description.ilike(f"%{filters.description_search}%"),
                    Transaction.raw_description.ilike(f"%{filters.description_search}%")
                )
            )
    
    # Apply sorting
    sort_column = getattr(Transaction, sort_by, Transaction.date)
    if sort_order.lower() == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))
    
    # Include category information
    query = query.options(joinedload(Transaction.category))
    
    return query.offset(skip).limit(limit).all()

def update_transaction(
    db: Session, 
    transaction_id: int, 
    transaction_update: TransactionUpdate, 
    user_id: int
) -> Optional[Transaction]:
    """Update a transaction"""
    db_transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id
    ).first()
    
    if not db_transaction:
        return None
    
    # Update only provided fields
    update_data = transaction_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_transaction, field, value)
    
    db_transaction.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(db_transaction)
    return db_transaction

def delete_transaction(db: Session, transaction_id: int, user_id: int) -> bool:
    """Delete a transaction"""
    db_transaction = db.query(Transaction).filter(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id
    ).first()
    
    if not db_transaction:
        return False
    
    db.delete(db_transaction)
    db.commit()
    return True

def get_transaction_summary(
    db: Session, 
    user_id: int, 
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    category_id: Optional[int] = None
) -> TransactionSummary:
    """Get transaction summary statistics"""
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    if category_id:
        query = query.filter(Transaction.category_id == category_id)
    
    # Calculate totals
    income_total = query.filter(Transaction.transaction_type == TransactionType.income).with_entities(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).scalar() or Decimal('0')
    
    expense_total = query.filter(Transaction.transaction_type == TransactionType.expense).with_entities(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).scalar() or Decimal('0')
    
    transaction_count = query.count()
    
    return TransactionSummary(
        total_income=income_total,
        total_expense=expense_total,
        net_amount=income_total - expense_total,
        transaction_count=transaction_count,
        period_start=start_date or datetime.min,
        period_end=end_date or datetime.max
    )

def get_spending_by_category(
    db: Session, 
    user_id: int, 
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Get spending grouped by category"""
    query = db.query(
        Category.name.label('category_name'),
        Category.type.label('category_type'),
        func.sum(Transaction.amount).label('total_amount'),
        func.count(Transaction.id).label('transaction_count')
    ).join(
        Transaction, Transaction.category_id == Category.id
    ).filter(
        Transaction.user_id == user_id
    ).group_by(Category.id, Category.name, Category.type)
    
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    
    results = query.all()
    
    return [
        {
            'category_name': result.category_name,
            'category_type': result.category_type,
            'total_amount': float(result.total_amount),
            'transaction_count': result.transaction_count
        }
        for result in results
    ]

def get_monthly_trends(
    db: Session, 
    user_id: int, 
    months: int = 12
) -> List[Dict[str, Any]]:
    """Get monthly spending/income trends"""
    query = db.query(
        extract('year', Transaction.date).label('year'),
        extract('month', Transaction.date).label('month'),
        Transaction.transaction_type,
        func.sum(Transaction.amount).label('total_amount'),
        func.count(Transaction.id).label('transaction_count')
    ).filter(
        Transaction.user_id == user_id,
        Transaction.date >= func.date_trunc('month', func.now() - func.make_interval(months=months))
    ).group_by(
        extract('year', Transaction.date),
        extract('month', Transaction.date),
        Transaction.transaction_type
    ).order_by(
        extract('year', Transaction.date),
        extract('month', Transaction.date),
        Transaction.transaction_type
    )
    
    results = query.all()
    
    return [
        {
            'year': int(result.year),
            'month': int(result.month),
            'transaction_type': result.transaction_type,
            'total_amount': float(result.total_amount),
            'transaction_count': result.transaction_count
        }
        for result in results
    ]

def get_top_merchants(
    db: Session, 
    user_id: int, 
    limit: int = 10,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """Get top merchants by spending"""
    query = db.query(
        Transaction.merchant,
        func.sum(Transaction.amount).label('total_amount'),
        func.count(Transaction.id).label('transaction_count'),
        func.avg(Transaction.amount).label('avg_amount')
    ).filter(
        Transaction.user_id == user_id,
        Transaction.merchant.isnot(None),
        Transaction.transaction_type == TransactionType.expense
    ).group_by(Transaction.merchant).order_by(desc('total_amount')).limit(limit)
    
    if start_date:
        query = query.filter(Transaction.date >= start_date)
    if end_date:
        query = query.filter(Transaction.date <= end_date)
    
    results = query.all()
    
    return [
        {
            'merchant': result.merchant,
            'total_amount': float(result.total_amount),
            'transaction_count': result.transaction_count,
            'avg_amount': float(result.avg_amount)
        }
        for result in results
    ]

def bulk_create_transactions(db: Session, transactions: List[TransactionCreate], user_id: int) -> List[Transaction]:
    """Create multiple transactions in bulk"""
    db_transactions = []
    for transaction_data in transactions:
        db_transaction = Transaction(
            user_id=user_id,
            **transaction_data.dict()
        )
        db_transactions.append(db_transaction)
    
    db.add_all(db_transactions)
    db.commit()
    
    # Refresh all objects to get their IDs
    for transaction in db_transactions:
        db.refresh(transaction)
    
    return db_transactions

def get_transaction_count(db: Session, user_id: int, filters: Optional[TransactionFilter] = None) -> int:
    """Get total count of transactions (for pagination)"""
    query = db.query(Transaction).filter(Transaction.user_id == user_id)
    
    # Apply same filters as get_transactions
    if filters:
        if filters.start_date:
            query = query.filter(Transaction.date >= filters.start_date)
        if filters.end_date:
            query = query.filter(Transaction.date <= filters.end_date)
        if filters.category_id:
            query = query.filter(Transaction.category_id == filters.category_id)
        if filters.transaction_type:
            query = query.filter(Transaction.transaction_type == filters.transaction_type)
        if filters.min_amount:
            query = query.filter(Transaction.amount >= filters.min_amount)
        if filters.max_amount:
            query = query.filter(Transaction.amount <= filters.max_amount)
        if filters.merchant:
            query = query.filter(Transaction.merchant.ilike(f"%{filters.merchant}%"))
        if filters.description_search:
            query = query.filter(
                or_(
                    Transaction.description.ilike(f"%{filters.description_search}%"),
                    Transaction.raw_description.ilike(f"%{filters.description_search}%")
                )
            )
    
    return query.count()