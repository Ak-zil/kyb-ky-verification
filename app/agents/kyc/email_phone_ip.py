from typing import Any, Dict, List, Optional
import ipaddress

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError


class EmailPhoneIpVerificationAgent(BaseAgent):
    """Agent for verifying email, phone number, and IP address in KYC workflow"""

    async def run(self) -> Dict[str, Any]:
        """
        Verify email, phone, and IP address
        
        Returns:
            Dict containing verification results
        """
        try:
            # Fetch data from verification_data table
            verification_data = await self.get_verification_data()
            user_data = verification_data.get("user", {}).get("user_data", {})
            sift_data = verification_data.get("user", {}).get("sift_data", {})
            
            # Extract email and phone from user data
            email = user_data.get("email", "")
            phone = user_data.get("phone", "")
            
            # Extract IP and device info from login activities
            login_activities = user_data.get("login_activities", [])
            ip_addresses = [activity.get("ip", "") for activity in login_activities]
            devices = [activity.get("device", "") for activity in login_activities]
            
            # Process checks
            checks = []
            
            # 1. Email Verification
            # In a real implementation, this would verify the email deliverability and reputation
            email_domain = email.split("@")[1] if "@" in email else ""
            suspicious_domains = ["tempmail.com", "throwaway.com", "fakeemail.com"]
            email_suspicious = any(domain in email_domain for domain in suspicious_domains)
            
            checks.append({
                "name": "Email Verification",
                "status": "failed" if email_suspicious else "passed",
                "details": f"Email domain is suspicious: {email_domain}" if email_suspicious else f"Email domain verified: {email_domain}"
            })
            
            # 2. Phone Verification
            # In a real implementation, this would verify the phone number carrier and type
            phone_verified = phone.startswith("+") and len(phone) > 10
            checks.append({
                "name": "Phone Verification",
                "status": "passed" if phone_verified else "failed",
                "details": f"Phone number verified: {phone}" if phone_verified else f"Invalid phone number format: {phone}"
            })
            
            # 3. IP Verification
            # In a real implementation, this would check IP reputation and geolocation
            ip_checks = []
            
            for ip in ip_addresses:
                if not ip:
                    continue
                    
                try:
                    # Check if IP is private
                    parsed_ip = ipaddress.ip_address(ip)
                    ip_private = parsed_ip.is_private
                    
                    # Check if IP is in a suspicious range (example check)
                    ip_suspicious = False  # This would integrate with IP reputation service
                    
                    ip_checks.append({
                        "ip": ip,
                        "private": ip_private,
                        "suspicious": ip_suspicious,
                        "status": "failed" if ip_suspicious else "passed"
                    })
                except ValueError:
                    ip_checks.append({
                        "ip": ip,
                        "status": "failed",
                        "details": f"Invalid IP format: {ip}"
                    })
            
            # Determine overall IP verification status
            ip_status = "passed"
            if not ip_checks:
                ip_status = "failed"
            elif any(check.get("status") == "failed" for check in ip_checks):
                ip_status = "failed"
                
            checks.append({
                "name": "IP Verification",
                "status": ip_status,
                "details": f"IPs verified: {len(ip_checks)}, Suspicious IPs: {sum(1 for check in ip_checks if check.get('suspicious', False))}",
                "ip_checks": ip_checks
            })
            
            # Use LLM to analyze email, phone, and IP verification
            risk_analysis = await self.extract_data_with_llm(
                data={
                    "checks": checks,
                    "email": email,
                    "phone": phone,
                    "ip_addresses": ip_addresses,
                    "devices": devices
                },
                prompt="""
                Analyze the email, phone, and IP verification results and identify any suspicious patterns.
                Consider the following:
                1. Is the email domain suspicious or associated with temporary email services?
                2. Is the phone number format valid and does it match the expected region?
                3. Are the IP addresses from suspicious regions or known proxy/VPN services?
                4. Are there any inconsistencies between login locations and provided address?
                
                Your response should include:
                1. An overall risk assessment for these verification factors
                2. Specific suspicious patterns identified, if any
                3. Recommendations for additional verification steps
                """
            )
            
            return {
                "agent_type": "EmailPhoneIpVerificationAgent",
                "status": "success",
                "details": risk_analysis.get("summary", "Email, phone, and IP verification completed"),
                "checks": checks
            }
            
        except Exception as e:
            self.logger.error(f"Email/Phone/IP verification error: {str(e)}")
            return {
                "agent_type": "EmailPhoneIpVerificationAgent",
                "status": "error",
                "details": f"Error during email, phone, and IP verification: {str(e)}",
                "checks": []
            }