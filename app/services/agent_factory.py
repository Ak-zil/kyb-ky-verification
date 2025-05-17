from typing import Any, Dict, List, Optional, Type

from app.agents.base import BaseAgent
from app.agents.data_acquisition import DataAcquisitionAgent
from app.agents.kyc.initial_diligence import InitialDiligenceAgent
from app.agents.kyc.govt_id import GovtIdVerificationAgent
from app.agents.kyc.id_selfie import IdSelfieVerificationAgent
from app.agents.kyc.aamva import AamvaVerificationAgent
from app.agents.kyc.email_phone_ip import EmailPhoneIpVerificationAgent
from app.agents.kyc.payment_behavior import PaymentBehaviorAgent
from app.agents.kyc.login_activities import LoginActivitiesAgent
from app.agents.kyc.sift import SiftVerificationAgent
from app.agents.kyc.id_check import IdCheckAgent
from app.agents.kyc.ofac import OfacVerificationAgent
from app.agents.kyb.normal_diligence import NormalDiligenceAgent
from app.agents.kyb.irs_match import IrsMatchAgent
from app.agents.kyb.sos_filings import SosFilingsAgent
from app.agents.kyb.ein_letter import EinLetterAgent
from app.agents.kyb.articles_incorporation import ArticlesIncorporationAgent
from app.agents.result_compilation import ResultCompilationAgent, BusinessResultCompilationAgent
from app.integrations.database import Database
from app.integrations.persona import PersonaClient
from app.integrations.sift import SiftClient
from app.utils.llm import BedrockClient
from app.utils.logging import get_logger


class AgentFactory:
    """Factory for creating verification agents"""

    def __init__(
        self,
        db_client: Database,
        bedrock_client: BedrockClient,
        persona_client: PersonaClient,
        sift_client: SiftClient,
    ):
        """
        Initialize agent factory
        
        Args:
            db_client: Database client
            bedrock_client: Amazon Bedrock client
            persona_client: Persona client
            sift_client: Sift client
        """
        self.db_client = db_client
        self.bedrock_client = bedrock_client
        self.persona_client = persona_client
        self.sift_client = sift_client
        self.logger = get_logger("AgentFactory")
        
        # Register agents
        self.agent_registry = {
            # Base agent
            "DataAcquisition": DataAcquisitionAgent,
            
            # KYC agents
            "InitialDiligence": InitialDiligenceAgent,
            "GovtIdVerification": GovtIdVerificationAgent,
            "IdSelfieVerification": IdSelfieVerificationAgent,
            "AamvaVerification": AamvaVerificationAgent,
            "EmailPhoneIpVerification": EmailPhoneIpVerificationAgent,
            "PaymentBehaviorAgent": PaymentBehaviorAgent,
            "LoginActivitiesAgent": LoginActivitiesAgent,
            "SiftVerificationAgent": SiftVerificationAgent,
            "IdCheckAgent": IdCheckAgent,
            "OfacVerificationAgent": OfacVerificationAgent,
            
            # KYB agents
            "NormalDiligence": NormalDiligenceAgent,
            "IrsMatchAgent": IrsMatchAgent,
            "SosFilingsAgent": SosFilingsAgent,
            "EinLetterAgent": EinLetterAgent,
            "ArticlesIncorporationAgent": ArticlesIncorporationAgent,
            
            # Result compilation agents
            "ResultCompilation": ResultCompilationAgent,
            "BusinessResultCompilation": BusinessResultCompilationAgent,
        }

    def create_agent(
        self, 
        agent_type: str, 
        verification_id: str,
        **kwargs
    ) -> BaseAgent:
        """
        Create an agent of the specified type
        
        Args:
            agent_type: Type of agent to create
            verification_id: ID of the verification
            **kwargs: Additional arguments for the agent
            
        Returns:
            Created agent instance
            
        Raises:
            ValueError: If agent type is not registered
        """
        try:
            # Get agent class
            agent_class = self.agent_registry.get(agent_type)
            if not agent_class:
                raise ValueError(f"Agent type {agent_type} not registered")
                
            # Create agent instance
            agent = agent_class(
                verification_id=verification_id,
                bedrock_client=self.bedrock_client,
                db_client=self.db_client,
                persona_client=self.persona_client,
                sift_client=self.sift_client,
                **kwargs
            )
            
            self.logger.info(f"Created agent of type {agent_type} for verification {verification_id}")
            return agent
            
        except Exception as e:
            self.logger.error(f"Error creating agent: {str(e)}")
            raise