from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import ipaddress

from app.agents.base import BaseAgent
from app.core.exceptions import AgentExecutionError


class LoginActivitiesAgent(BaseAgent):
    """Agent for analyzing login activities in KYC workflow"""

    async def run(self) -> Dict[str, Any]:
        """
        Analyze login activities
        
        Returns:
            Dict containing verification results
        """
        try:
            # Fetch data from verification_data table
            verification_data = await self.get_verification_data()
            user_data = verification_data.get("user", {}).get("user_data", {})
            sift_data = verification_data.get("user", {}).get("sift_data", {})
            
            # Extract login activities
            login_activities = user_data.get("login_activities", [])
            
            # Extract Sift login activities
            sift_activities = sift_data.get("user", {}).get("activities", [])
            sift_logins = [a for a in sift_activities if a.get("type") == "login"]
            
            # Process checks
            checks = []
            
            # 1. Login Location Analysis
            locations = [activity.get("location", "") for activity in login_activities]
            unique_locations = set(locations)
            
            # Check for impossible travel (logins from different locations in a short time)
            impossible_travel = False
            login_activities_sorted = sorted(
                [a for a in login_activities if a.get("date")],
                key=lambda x: datetime.fromisoformat(x.get("date"))
            )
            
            for i in range(1, len(login_activities_sorted)):
                current = login_activities_sorted[i]
                previous = login_activities_sorted[i-1]
                
                current_date = datetime.fromisoformat(current.get("date"))
                previous_date = datetime.fromisoformat(previous.get("date"))
                
                current_location = current.get("location", "")
                previous_location = previous.get("location", "")
                
                # If different locations and time difference < 2 hours, flag as impossible travel
                if (current_location != previous_location and 
                    (current_date - previous_date) < timedelta(hours=2)):
                    impossible_travel = True
                    break
            
            checks.append({
                "name": "Login Location Analysis",
                "status": "failed" if impossible_travel else "passed",
                "details": f"Unique locations: {len(unique_locations)}, Impossible travel detected: {impossible_travel}"
            })
            
            # 2. Device Analysis
            devices = [activity.get("device", "") for activity in login_activities]
            unique_devices = set(devices)
            
            # Check for excessive number of devices
            excessive_devices = len(unique_devices) > 5  # Arbitrary threshold
            
            checks.append({
                "name": "Device Analysis",
                "status": "failed" if excessive_devices else "passed",
                "details": f"Unique devices: {len(unique_devices)}, Excessive devices: {excessive_devices}"
            })
            
            # 3. IP Analysis
            ips = [activity.get("ip", "") for activity in login_activities]
            
            # Check for suspicious IPs
            suspicious_ips = []
            for ip in ips:
                if not ip:
                    continue
                    
                try:
                    # In a real system, this would integrate with IP reputation services
                    parsed_ip = ipaddress.ip_address(ip)
                    if parsed_ip.is_private:
                        suspicious_ips.append(ip)
                except ValueError:
                    suspicious_ips.append(ip)
            
            checks.append({
                "name": "IP Analysis",
                "status": "failed" if suspicious_ips else "passed",
                "details": f"Suspicious IPs: {len(suspicious_ips)}"
            })
            
            # 4. Login Failure Analysis
            failed_logins = [a for a in sift_logins if a.get("status") != "success"]
            
            # Check for excessive failed login attempts
            excessive_failures = len(failed_logins) > 3  # Arbitrary threshold
            
            checks.append({
                "name": "Login Failure Analysis",
                "status": "failed" if excessive_failures else "passed",
                "details": f"Failed login attempts: {len(failed_logins)}, Excessive failures: {excessive_failures}"
            })
            
            # Use LLM to analyze login patterns
            risk_analysis = await self.extract_data_with_llm(
                data={
                    "checks": checks,
                    "login_activities": login_activities,
                    "sift_logins": sift_logins
                },
                prompt="""
                Analyze the login activities to identify any suspicious patterns or security risks.
                Consider:
                1. Login locations and potential impossible travel between locations
                2. Number and variety of devices used
                3. IP addresses and their reputation
                4. Failed login attempts
                
                Your response should include:
                1. An overall risk assessment of the login behavior
                2. Specific suspicious patterns or anomalies detected
                3. Recommendations for additional security measures
                """
            )
            
            return {
                "agent_type": "LoginActivitiesAgent",
                "status": "success",
                "details": risk_analysis.get("summary", "Login activities analysis completed"),
                "checks": checks
            }
            
        except Exception as e:
            self.logger.error(f"Login activities analysis error: {str(e)}")
            return {
                "agent_type": "LoginActivitiesAgent",
                "status": "error",
                "details": f"Error during login activities analysis: {str(e)}",
                "checks": []
            }