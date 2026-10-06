# app/api/v1/endpoints/transaction.py
from datetime import datetime
from typing import List, Optional
import csv
import io
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.transaction import TransactionType
from app.crud import transaction as transaction_crud
from app.schemas.transaction import (
    TransactionCreate, TransactionUpdate, TransactionOut, TransactionSummary,
    TransactionFilter, BulkTransactionCreate
)

router = APIRouter()

@router.post("/", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_transaction(
    transaction_data: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new transaction"""
    # Validate category belongs to user if provided
    if transaction_data.category_id:
        from app.models.category import Category
        category = db.query(Category).filter(
            Category.id == transaction_data.category_id,
            Category.user_id == current_user.id
        ).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found or doesn't belong to user"
            )
    
    transaction = transaction_crud.create_transaction(db, transaction_data, current_user.id)
    
    # Check for budget violations and unusual spending patterns
    alerts_created = []
    if transaction.transaction_type == TransactionType.expense and transaction.category_id:
        from app.services.budget_tracker import budget_tracker
        
        # Check budgets and create alerts
        budget_alerts = budget_tracker.check_budget_after_transaction(
            db, current_user.id, transaction
        )
        alerts_created.extend(budget_alerts)
        
        # Check for unusual spending
        unusual_spending = budget_tracker.detect_unusual_spending(
            db, current_user.id, transaction
        )
        if unusual_spending:
            # Create unusual spending alert
            from app.crud import alert as alert_crud
            alert = alert_crud.create_transaction_alert(
                db=db,
                user_id=current_user.id,
                transaction_id=transaction.id,
                alert_type=unusual_spending['alert_type'],
                title="Unusual Spending Detected",
                message=(
                    f"Large transaction detected: ${unusual_spending['amount']:.2f} "
                    f"(Average: ${unusual_spending['average_amount']:.2f})"
                ),
                priority="medium"
            )
            alerts_created.append({
                'alert_id': alert.id,
                'type': 'unusual_spending',
                'message': alert.message
            })
    
    # Enrich response with alerts if any were created
    response_data = transaction.__dict__.copy()
    if alerts_created:
        response_data['alerts_generated'] = alerts_created
    
    return TransactionOut(**response_data)

@router.get("/", response_model=List[TransactionOut])
def get_transactions(
    skip: int = Query(0, ge=0, description="Number of transactions to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of transactions to return"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    transaction_type: Optional[TransactionType] = Query(None, description="Filter by transaction type"),
    min_amount: Optional[float] = Query(None, ge=0, description="Minimum amount filter"),
    max_amount: Optional[float] = Query(None, ge=0, description="Maximum amount filter"),
    merchant: Optional[str] = Query(None, description="Filter by merchant name"),
    description_search: Optional[str] = Query(None, description="Search in description"),
    sort_by: str = Query("date", regex="^(date|amount|description|merchant)$", description="Sort field"),
    sort_order: str = Query("desc", regex="^(asc|desc)$", description="Sort order"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get transactions with filtering and pagination"""
    filters = TransactionFilter(
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        transaction_type=transaction_type,
        min_amount=min_amount,
        max_amount=max_amount,
        merchant=merchant,
        description_search=description_search
    )
    
    transactions = transaction_crud.get_transactions(
        db, current_user.id, skip, limit, filters, sort_by, sort_order
    )
    
    # Enrich with category information
    enriched_transactions = []
    for transaction in transactions:
        transaction_dict = {
            **transaction.__dict__,
            'category_name': transaction.category.name if transaction.category else None,
            'category_type': transaction.category.type if transaction.category else None
        }
        enriched_transactions.append(TransactionOut(**transaction_dict))
    
    return enriched_transactions

@router.get("/count")
def get_transaction_count(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    category_id: Optional[int] = Query(None),
    transaction_type: Optional[TransactionType] = Query(None),
    min_amount: Optional[float] = Query(None, ge=0),
    max_amount: Optional[float] = Query(None, ge=0),
    merchant: Optional[str] = Query(None),
    description_search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get total count of transactions matching filters"""
    filters = TransactionFilter(
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        transaction_type=transaction_type,
        min_amount=min_amount,
        max_amount=max_amount,
        merchant=merchant,
        description_search=description_search
    )
    
    count = transaction_crud.get_transaction_count(db, current_user.id, filters)
    return {"count": count}

@router.get("/summary", response_model=TransactionSummary)
def get_transaction_summary(
    start_date: Optional[datetime] = Query(None, description="Summary start date"),
    end_date: Optional[datetime] = Query(None, description="Summary end date"),
    category_id: Optional[int] = Query(None, description="Filter by category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get transaction summary statistics"""
    return transaction_crud.get_transaction_summary(
        db, current_user.id, start_date, end_date, category_id
    )

@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get a specific transaction"""
    transaction = transaction_crud.get_transaction(db, transaction_id, current_user.id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Enrich with category information
    transaction_dict = {
        **transaction.__dict__,
        'category_name': transaction.category.name if transaction.category else None,
        'category_type': transaction.category.type if transaction.category else None
    }
    
    return TransactionOut(**transaction_dict)

@router.put("/{transaction_id}", response_model=TransactionOut)
def update_transaction(
    transaction_id: int,
    transaction_update: TransactionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a transaction"""
    # Validate category belongs to user if being updated
    if transaction_update.category_id:
        from app.models.category import Category
        category = db.query(Category).filter(
            Category.id == transaction_update.category_id,
            Category.user_id == current_user.id
        ).first()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found or doesn't belong to user"
            )
    
    transaction = transaction_crud.update_transaction(
        db, transaction_id, transaction_update, current_user.id
    )
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    # Enrich with category information
    transaction_dict = {
        **transaction.__dict__,
        'category_name': transaction.category.name if transaction.category else None,
        'category_type': transaction.category.type if transaction.category else None
    }
    
    return TransactionOut(**transaction_dict)

@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a transaction"""
    success = transaction_crud.delete_transaction(db, transaction_id, current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    return None

@router.post("/bulk", response_model=List[TransactionOut])
def bulk_create_transactions(
    bulk_data: BulkTransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create multiple transactions in bulk"""
    # Validate all categories belong to user
    category_ids = {t.category_id for t in bulk_data.transactions if t.category_id}
    if category_ids:
        from app.models.category import Category
        valid_categories = db.query(Category.id).filter(
            Category.id.in_(category_ids),
            Category.user_id == current_user.id
        ).all()
        valid_category_ids = {cat.id for cat in valid_categories}
        
        for transaction_data in bulk_data.transactions:
            if transaction_data.category_id and transaction_data.category_id not in valid_category_ids:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Category {transaction_data.category_id} not found or doesn't belong to user"
                )
    
    transactions = transaction_crud.bulk_create_transactions(
        db, bulk_data.transactions, current_user.id
    )
    
    return [TransactionOut(**transaction.__dict__) for transaction in transactions]

# Analytics endpoints
@router.get("/analytics/by-category")
def get_spending_by_category(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get spending grouped by category"""
    return transaction_crud.get_spending_by_category(db, current_user.id, start_date, end_date)

@router.get("/analytics/monthly-trends")
def get_monthly_trends(
    months: int = Query(12, ge=1, le=24, description="Number of months to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get monthly spending/income trends"""
    return transaction_crud.get_monthly_trends(db, current_user.id, months)

@router.get("/analytics/top-merchants")
def get_top_merchants(
    limit: int = Query(10, ge=1, le=50),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get top merchants by spending"""
    return transaction_crud.get_top_merchants(db, current_user.id, limit, start_date, end_date)

@router.post("/upload-csv")
async def upload_csv(
    file: UploadFile = File(...),
    category_id: Optional[int] = Query(None, description="Default category for transactions without category"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Upload transactions from CSV file"""
    
    # Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file"
        )
    
    # Read and parse CSV content
    try:
        content = await file.read()
        csv_content = content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        
        # Expected CSV columns: date, amount, description, merchant, transaction_type, category_name
        required_columns = {'date', 'amount', 'description', 'transaction_type'}
        csv_columns = set(csv_reader.fieldnames or [])
        
        if not required_columns.issubset(csv_columns):
            missing_columns = required_columns - csv_columns
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing required columns: {missing_columns}"
            )
        
        transactions_to_create = []
        errors = []
        
        # Get user's categories for mapping
        from app.models.category import Category
        user_categories = db.query(Category).filter(Category.user_id == current_user.id).all()
        category_map = {cat.name.lower(): cat.id for cat in user_categories}
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 because row 1 is headers
            try:
                # Parse date
                try:
                    transaction_date = datetime.strptime(row['date'], '%Y-%m-%d')
                except ValueError:
                    try:
                        transaction_date = datetime.strptime(row['date'], '%m/%d/%Y')
                    except ValueError:
                        errors.append(f"Row {row_num}: Invalid date format. Use YYYY-MM-DD or MM/DD/YYYY")
                        continue
                
                # Parse amount
                try:
                    amount = float(row['amount'].replace('$', '').replace(',', ''))
                    if amount <= 0:
                        errors.append(f"Row {row_num}: Amount must be positive")
                        continue
                except ValueError:
                    errors.append(f"Row {row_num}: Invalid amount format")
                    continue
                
                # Validate transaction type
                transaction_type = row['transaction_type'].lower()
                if transaction_type not in ['income', 'expense']:
                    errors.append(f"Row {row_num}: Transaction type must be 'income' or 'expense'")
                    continue
                
                # Map category
                category_id_for_transaction = category_id  # Default
                if 'category_name' in row and row['category_name']:
                    category_name = row['category_name'].lower().strip()
                    if category_name in category_map:
                        category_id_for_transaction = category_map[category_name]
                    else:
                        errors.append(f"Row {row_num}: Category '{row['category_name']}' not found")
                        continue
                
                # Create transaction data
                transaction_data = TransactionCreate(
                    date=transaction_date,
                    amount=amount,
                    description=row['description'].strip(),
                    merchant=row.get('merchant', '').strip() or None,
                    transaction_type=TransactionType(transaction_type),
                    category_id=category_id_for_transaction,
                    raw_description=row.get('raw_description', row['description']).strip(),
                    reference_id=row.get('reference_id', '').strip() or None,
                    notes=row.get('notes', '').strip() or None
                )
                
                transactions_to_create.append(transaction_data)
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        # If there are errors but some valid transactions, ask user what to do
        if errors and transactions_to_create:
            return {
                "status": "partial_success",
                "message": f"{len(transactions_to_create)} transactions ready to import, {len(errors)} errors found",
                "valid_transactions": len(transactions_to_create),
                "errors": errors,
                "proceed_url": "/transactions/upload-csv/confirm"  # Future implementation
            }
        
        # If only errors, return them
        if errors and not transactions_to_create:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"message": "No valid transactions found", "errors": errors}
            )
        
        # Bulk create transactions
        created_transactions = transaction_crud.bulk_create_transactions(
            db, transactions_to_create, current_user.id
        )
        
        return {
            "status": "success",
            "message": f"Successfully imported {len(created_transactions)} transactions",
            "imported_count": len(created_transactions),
            "transactions": [TransactionOut(**t.__dict__) for t in created_transactions[:10]]  # Return first 10
        }
        
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File encoding not supported. Please use UTF-8 encoded CSV"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing CSV file: {str(e)}"
        )

@router.get("/csv-template")
def download_csv_template():
    """Download CSV template for transaction import"""
    from fastapi.responses import StreamingResponse
    
    template_content = '''date,amount,description,merchant,transaction_type,category_name,reference_id,notes
2024-01-15,25.50,Coffee and pastry,Starbucks,expense,Food & Dining,TXN123,Morning coffee
2024-01-15,3000.00,Salary deposit,ABC Company,income,Salary,,Monthly salary
2024-01-16,45.99,Grocery shopping,Walmart,expense,Groceries,TXN124,Weekly groceries
'''
    
    def generate():
        yield template_content
    
    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=transaction_template.csv"}
    )

# Categorization endpoints
@router.post("/categorize")
def categorize_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Auto-categorize a specific transaction"""
    from app.services.categorization import categorizer
    
    transaction = transaction_crud.get_transaction(db, transaction_id, current_user.id)
    if not transaction:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found"
        )
    
    suggested_category_id = categorizer.categorize_transaction(
        transaction.description,
        transaction.merchant,
        float(transaction.amount),
        db,
        current_user.id
    )
    
    return {
        "transaction_id": transaction_id,
        "suggested_category_id": suggested_category_id,
        "current_category_id": transaction.category_id
    }

@router.post("/suggest-categories")
def suggest_categories(
    description: str,
    merchant: Optional[str] = None,
    limit: int = Query(3, ge=1, le=10),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get category suggestions for transaction data"""
    from app.services.categorization import categorizer
    
    suggestions = categorizer.suggest_categories(
        description, merchant, db, current_user.id, limit
    )
    
    return {"suggestions": suggestions}

@router.post("/bulk-categorize")
def bulk_categorize_transactions(
    uncategorized_only: bool = Query(True, description="Only categorize uncategorized transactions"),
    category_id: Optional[int] = Query(None, description="Filter by specific category to re-categorize"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of transactions to categorize"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk categorize transactions"""
    from app.services.categorization import categorizer
    from app.models.transaction import Transaction
    
    # Get transactions to categorize
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id)
    
    if uncategorized_only:
        query = query.filter(Transaction.category_id.is_(None))
    elif category_id:
        query = query.filter(Transaction.category_id == category_id)
    
    transactions = query.limit(limit).all()
    
    if not transactions:
        return {
            "message": "No transactions found to categorize",
            "categorized_count": 0,
            "results": []
        }
    
    # Bulk categorize
    results = categorizer.bulk_categorize(transactions, db, current_user.id)
    
    # Update transactions with suggested categories
    updated_count = 0
    categorization_results = []
    
    for transaction_id, suggested_category_id in results.items():
        if suggested_category_id:
            # Update transaction
            transaction = db.query(Transaction).filter(
                Transaction.id == transaction_id,
                Transaction.user_id == current_user.id
            ).first()
            
            if transaction:
                old_category_id = transaction.category_id
                transaction.category_id = suggested_category_id
                updated_count += 1
                
                categorization_results.append({
                    "transaction_id": transaction_id,
                    "description": transaction.description,
                    "old_category_id": old_category_id,
                    "new_category_id": suggested_category_id
                })
    
    db.commit()
    
    return {
        "message": f"Successfully categorized {updated_count} transactions",
        "categorized_count": updated_count,
        "total_processed": len(transactions),
        "results": categorization_results
    }