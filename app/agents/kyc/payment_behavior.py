from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError


class PaymentBehaviorAgent(BaseAgent):
    """Agent for analyzing payment behavior in KYC workflow"""

    async def run(self) -> Dict[str, Any]:
        """
        Analyze payment behavior
        
        Returns:
            Dict containing verification results
        """
        try:
            # Fetch data from verification_data table
            verification_data = await self.get_verification_data()
            user_data = verification_data.get("user", {}).get("user_data", {})
            sift_data = verification_data.get("user", {}).get("sift_data", {})
            
            # Extract bank accounts and transactions
            bank_accounts = user_data.get("bank_accounts", [])
            
            # Extract Sift payment abuse score
            payment_abuse_score = sift_data.get("scores", {}).get("payment_abuse", 0)
            
            # Process checks
            checks = []
            
            # 1. Bank Account Verification
            bank_verified = any(account.get("verified", False) for account in bank_accounts)
            checks.append({
                "name": "Bank Account Verification",
                "status": "passed" if bank_verified else "failed",
                "details": f"Verified bank accounts: {sum(1 for account in bank_accounts if account.get('verified', False))}"
            })
            
            # 2. Transaction History Analysis
            all_transactions = []
            for account in bank_accounts:
                transactions = account.get("last_transactions", [])
                all_transactions.extend(transactions)
            
            # Analyze transaction patterns
            if all_transactions:
                # Sort transactions by date
                transactions_sorted = sorted(
                    all_transactions, 
                    key=lambda x: datetime.fromisoformat(x.get("date")) if x.get("date") else datetime.min
                )
                
                # Check for suspicious transaction patterns
                large_transactions = [t for t in transactions_sorted if t.get("amount", 0) > 5000]
                rapid_transactions = []
                
                for i in range(1, len(transactions_sorted)):
                    current_date = datetime.fromisoformat(transactions_sorted[i].get("date"))
                    prev_date = datetime.fromisoformat(transactions_sorted[i-1].get("date"))
                    if (current_date - prev_date) < timedelta(minutes=10):
                        rapid_transactions.append((transactions_sorted[i-1], transactions_sorted[i]))
                
                transaction_risk = (
                    len(large_transactions) > 2 or 
                    len(rapid_transactions) > 1
                )
                
                checks.append({
                    "name": "Transaction Pattern Analysis",
                    "status": "failed" if transaction_risk else "passed",
                    "details": f"Large transactions: {len(large_transactions)}, Rapid transactions: {len(rapid_transactions)}"
                })
            else:
                checks.append({
                    "name": "Transaction Pattern Analysis",
                    "status": "not_applicable",
                    "details": "No transaction history available"
                })
            
            # 3. Sift Payment Abuse Score
            payment_score_threshold = 50
            checks.append({
                "name": "Sift Payment Abuse Score",
                "status": "failed" if payment_abuse_score > payment_score_threshold else "passed",
                "details": f"Payment abuse score: {payment_abuse_score}, threshold: {payment_score_threshold}"
            })
            
            # Use LLM to analyze payment behavior
            risk_analysis = await self.extract_data_with_llm(
                data={
                    "checks": checks,
                    "bank_accounts": bank_accounts,
                    "all_transactions": all_transactions,
                    "payment_abuse_score": payment_abuse_score
                },
                prompt="""
                Analyze the payment behavior and bank account information to identify any 
                suspicious patterns or fraud indicators. Consider:
                1. Bank account verification status
                2. Transaction patterns, focusing on unusually large or frequent transactions
                3. Sift payment abuse risk score
                
                Your response should include:
                1. An overall risk assessment of the payment behavior
                2. Specific suspicious patterns or red flags identified
                3. Recommendations for additional verification or monitoring
                """
            )
            
            return {
                "agent_type": "PaymentBehaviorAgent",
                "status": "success",
                "details": risk_analysis.get("summary", "Payment behavior analysis completed"),
                "checks": checks
            }
            
        except Exception as e:
            self.logger.error(f"Payment behavior analysis error: {str(e)}")
            return {
                "agent_type": "PaymentBehaviorAgent",
                "status": "error",
                "details": f"Error during payment behavior analysis: {str(e)}",
                "checks": []
            }