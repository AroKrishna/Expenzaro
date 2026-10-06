# app/services/categorization.py
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from app.models.category import Category, CategoryType
from app.models.transaction import Transaction

class TransactionCategorizer:
    """
    Service for automatically categorizing transactions using rule-based approach.
    Can be extended with ML models in the future.
    """
    
    def __init__(self):
        # Define category rules with keywords and merchant patterns
        self.category_rules = {
            'food_dining': {
                'type': CategoryType.expense,
                'keywords': [
                    'restaurant', 'cafe', 'coffee', 'pizza', 'burger', 'food', 'dining',
                    'lunch', 'dinner', 'breakfast', 'meal', 'bistro', 'grill', 'bar'
                ],
                'merchants': [
                    'mcdonalds', 'starbucks', 'subway', 'pizza hut', 'dominos', 'kfc',
                    'burger king', 'taco bell', 'chipotle', 'panera'
                ]
            },
            'groceries': {
                'type': CategoryType.expense,
                'keywords': [
                    'grocery', 'supermarket', 'market', 'food store', 'fresh', 'produce',
                    'organic', 'deli', 'bakery', 'butcher'
                ],
                'merchants': [
                    'walmart', 'target', 'kroger', 'safeway', 'whole foods', 'costco',
                    'trader joes', 'publix', 'wegmans', 'aldi'
                ]
            },
            'transportation': {
                'type': CategoryType.expense,
                'keywords': [
                    'gas', 'fuel', 'parking', 'toll', 'taxi', 'uber', 'lyft', 'bus',
                    'train', 'metro', 'transit', 'transport', 'auto', 'car'
                ],
                'merchants': [
                    'shell', 'exxon', 'bp', 'chevron', 'mobil', 'uber', 'lyft',
                    'parking', 'metro', 'transit'
                ]
            },
            'entertainment': {
                'type': CategoryType.expense,
                'keywords': [
                    'movie', 'cinema', 'theater', 'netflix', 'spotify', 'music',
                    'game', 'entertainment', 'streaming', 'subscription', 'concert'
                ],
                'merchants': [
                    'netflix', 'spotify', 'amazon prime', 'hulu', 'disney plus',
                    'youtube premium', 'amc theaters', 'steam', 'playstation'
                ]
            },
            'shopping': {
                'type': CategoryType.expense,
                'keywords': [
                    'amazon', 'ebay', 'shop', 'store', 'retail', 'clothing', 'shoes',
                    'electronics', 'best buy', 'home depot', 'lowes'
                ],
                'merchants': [
                    'amazon', 'ebay', 'best buy', 'home depot', 'lowes', 'macys',
                    'nordstrom', 'gap', 'nike', 'apple store'
                ]
            },
            'utilities': {
                'type': CategoryType.expense,
                'keywords': [
                    'electric', 'electricity', 'gas bill', 'water', 'internet', 'phone',
                    'cable', 'utility', 'bill', 'service'
                ],
                'merchants': [
                    'comcast', 'verizon', 'att', 'tmobile', 'sprint'
                ]
            },
            'healthcare': {
                'type': CategoryType.expense,
                'keywords': [
                    'medical', 'doctor', 'hospital', 'pharmacy', 'health', 'dental',
                    'clinic', 'cvs', 'walgreens', 'prescription'
                ],
                'merchants': [
                    'cvs', 'walgreens', 'rite aid', 'kaiser', 'blue cross'
                ]
            },
            'salary': {
                'type': CategoryType.income,
                'keywords': [
                    'salary', 'payroll', 'wages', 'pay', 'income', 'deposit',
                    'direct deposit', 'paycheck'
                ],
                'merchants': []
            },
            'investment': {
                'type': CategoryType.income,
                'keywords': [
                    'dividend', 'interest', 'investment', 'stock', 'bond', 'return',
                    'capital gain', 'portfolio'
                ],
                'merchants': [
                    'fidelity', 'charles schwab', 'vanguard', 'robinhood', 'etrade'
                ]
            }
        }
    
    def categorize_transaction(
        self, 
        description: str, 
        merchant: Optional[str], 
        amount: float,
        db: Session,
        user_id: int
    ) -> Optional[int]:
        """
        Categorize a transaction and return the category ID.
        
        Args:
            description: Transaction description
            merchant: Merchant name (optional)
            amount: Transaction amount
            db: Database session
            user_id: User ID for category lookup
            
        Returns:
            Category ID if found, None otherwise
        """
        # Get user's categories
        user_categories = db.query(Category).filter(Category.user_id == user_id).all()
        category_map = {cat.name.lower(): cat for cat in user_categories}
        
        # Combine description and merchant for analysis
        text_to_analyze = f"{description} {merchant or ''}".lower()
        
        # Try rule-based categorization first
        category_scores = {}
        
        for category_name, rules in self.category_rules.items():
            score = 0
            
            # Check keywords in description/merchant
            for keyword in rules['keywords']:
                if keyword in text_to_analyze:
                    score += 2
            
            # Check merchant matches (higher weight)
            for merchant_pattern in rules['merchants']:
                if merchant and merchant_pattern in merchant.lower():
                    score += 5
            
            # Exact merchant match (highest weight)
            if merchant and merchant.lower() in rules['merchants']:
                score += 10
            
            if score > 0:
                category_scores[category_name] = score
        
        # Find best matching category
        if category_scores:
            best_category = max(category_scores.items(), key=lambda x: x[1])[0]
            
            # Map to user's actual categories
            category_mappings = {
                'food_dining': ['food & dining', 'restaurants', 'food', 'dining'],
                'groceries': ['groceries', 'food & groceries', 'supermarket'],
                'transportation': ['transportation', 'transport', 'travel', 'gas'],
                'entertainment': ['entertainment', 'movies', 'streaming'],
                'shopping': ['shopping', 'retail', 'clothing'],
                'utilities': ['utilities', 'bills', 'services'],
                'healthcare': ['healthcare', 'medical', 'health'],
                'salary': ['salary', 'income', 'wages'],
                'investment': ['investment', 'dividends', 'stocks']
            }
            
            # Try to find matching user category
            possible_names = category_mappings.get(best_category, [best_category])
            for possible_name in possible_names:
                if possible_name in category_map:
                    return category_map[possible_name].id
        
        # If no rule-based match, try fuzzy matching with user's categories
        return self._fuzzy_match_category(text_to_analyze, user_categories)
    
    def _fuzzy_match_category(self, text: str, categories: List[Category]) -> Optional[int]:
        """
        Perform fuzzy matching with user's existing categories.
        """
        best_match = None
        best_score = 0
        
        for category in categories:
            # Simple keyword matching with category name
            category_words = category.name.lower().split()
            score = 0
            
            for word in category_words:
                if word in text:
                    score += len(word)  # Longer words get higher scores
            
            if score > best_score and score >= 3:  # Minimum threshold
                best_score = score
                best_match = category
        
        return best_match.id if best_match else None
    
    def suggest_categories(
        self, 
        description: str, 
        merchant: Optional[str],
        db: Session,
        user_id: int,
        limit: int = 3
    ) -> List[Dict]:
        """
        Suggest multiple possible categories for a transaction.
        
        Returns:
            List of suggested categories with confidence scores
        """
        user_categories = db.query(Category).filter(Category.user_id == user_id).all()
        text_to_analyze = f"{description} {merchant or ''}".lower()
        
        suggestions = []
        
        # Rule-based suggestions
        for category_name, rules in self.category_rules.items():
            score = 0
            matched_keywords = []
            
            for keyword in rules['keywords']:
                if keyword in text_to_analyze:
                    score += 2
                    matched_keywords.append(keyword)
            
            for merchant_pattern in rules['merchants']:
                if merchant and merchant_pattern in merchant.lower():
                    score += 5
                    matched_keywords.append(f"merchant: {merchant_pattern}")
            
            if score > 0:
                # Find corresponding user category
                user_category = None
                category_mappings = {
                    'food_dining': ['food & dining', 'restaurants', 'food', 'dining'],
                    'groceries': ['groceries', 'food & groceries', 'supermarket'],
                    'transportation': ['transportation', 'transport', 'travel', 'gas'],
                    'entertainment': ['entertainment', 'movies', 'streaming'],
                    'shopping': ['shopping', 'retail', 'clothing'],
                    'utilities': ['utilities', 'bills', 'services'],
                    'healthcare': ['healthcare', 'medical', 'health'],
                    'salary': ['salary', 'income', 'wages'],
                    'investment': ['investment', 'dividends', 'stocks']
                }
                
                possible_names = category_mappings.get(category_name, [category_name])
                category_map = {cat.name.lower(): cat for cat in user_categories}
                
                for possible_name in possible_names:
                    if possible_name in category_map:
                        user_category = category_map[possible_name]
                        break
                
                if user_category:
                    confidence = min(score * 10, 100)  # Cap at 100%
                    suggestions.append({
                        'category_id': user_category.id,
                        'category_name': user_category.name,
                        'category_type': user_category.type,
                        'confidence': confidence,
                        'matched_keywords': matched_keywords,
                        'reason': f"Matched {len(matched_keywords)} keywords/patterns"
                    })
        
        # Sort by confidence and return top suggestions
        suggestions.sort(key=lambda x: x['confidence'], reverse=True)
        return suggestions[:limit]
    
    def learn_from_user_categorization(
        self, 
        description: str, 
        merchant: Optional[str], 
        category_id: int,
        db: Session
    ):
        """
        Learn from user's manual categorization to improve future predictions.
        This is a placeholder for future ML model training.
        """
        # In a full implementation, this would:
        # 1. Store the user's categorization as training data
        # 2. Update model weights or rules
        # 3. Improve future predictions
        pass
    
    def bulk_categorize(
        self, 
        transactions: List[Transaction],
        db: Session,
        user_id: int
    ) -> Dict[int, Optional[int]]:
        """
        Categorize multiple transactions in bulk.
        
        Returns:
            Dictionary mapping transaction ID to suggested category ID
        """
        results = {}
        
        for transaction in transactions:
            if not transaction.category_id:  # Only categorize uncategorized transactions
                suggested_category = self.categorize_transaction(
                    transaction.description,
                    transaction.merchant,
                    float(transaction.amount),
                    db,
                    user_id
                )
                results[transaction.id] = suggested_category
        
        return results

# Global instance
categorizer = TransactionCategorizer()