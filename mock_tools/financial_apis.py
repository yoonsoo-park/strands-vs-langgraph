import json
from typing import Dict, Any

# Mock Customer Database
# In a real nCino environment, this would hit Salesforce or a Core Banking system
MOCK_CUSTOMER_DATA = {
    "123": {
        "name": "Jane Doe",
        "account_balance": 1500.50,
        "credit_score": 750,
        "active_loans": [
            {"type": "Auto", "balance": 12000.00, "status": "Current"}
        ]
    },
    "456": {
        "name": "John Smith",
        "account_balance": -150.00, # Overdrawn
        "credit_score": 620,
        "active_loans": []
    }
}

def get_customer_balance(customer_id: str) -> str:
    """
    Retrieves the current account balance for a given customer ID.
    """
    print(f"[Tools] Calling get_customer_balance for {customer_id}")
    customer = MOCK_CUSTOMER_DATA.get(customer_id)
    if not customer:
        return json.dumps({"error": f"Customer ID {customer_id} not found."})
    
    return json.dumps({
        "customer_name": customer["name"],
        "account_balance": customer["account_balance"]
    })

def check_loan_eligibility(customer_id: str, requested_amount: float) -> str:
    """
    Evaluates if a customer is eligible for a new loan based on their credit score and current balance.
    """
    print(f"[Tools] Calling check_loan_eligibility for {customer_id}, amount: {requested_amount}")
    customer = MOCK_CUSTOMER_DATA.get(customer_id)
    if not customer:
        return json.dumps({"error": f"Customer ID {customer_id} not found."})

    # Basic mock business logic for loan approval
    if customer["credit_score"] < 650:
        return json.dumps({
            "eligible": False, 
            "reason": "Credit score below minimum requirement of 650."
        })
    
    if customer["account_balance"] < 0:
        return json.dumps({
            "eligible": False, 
            "reason": "Account is currently overdrawn. Must have positive balance."
        })
        
    if requested_amount > 50000:
         return json.dumps({
            "eligible": False, 
            "reason": "Requested amount exceeds maximum limit of $50,000 for standard loans."
        })

    return json.dumps({
        "eligible": True,
        "max_approved_amount": min(requested_amount, 50000),
        "interest_rate_estimate": "5.5%" if customer["credit_score"] > 700 else "8.0%"
    })
