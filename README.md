# Verification System - KYC/KYB Automation Tool

## Overview

This system provides automated KYC (Know Your Customer) and KYB (Know Your Business) verification using an agentic approach with Amazon Bedrock Deepseek as the LLM. It is designed to verify customer and business data, process verification workflows, and provide secure API endpoints for integration.

## Features

- **KYC Verification**: Verify individual user identity and assess risk
- **KYB Verification**: Verify business legitimacy and assess risk
- **UBO Verification**: Verify Ultimate Beneficial Owners as part of KYB process
- **Agentic Architecture**: Multiple specialized agents for different verification tasks
- **LLM Integration**: Amazon Bedrock Deepseek for intelligent data analysis
- **Secure API**: JWT authentication for admin users and API key authentication for client applications
- **Dual Database Architecture**: 
  - PostgreSQL for application data and verification results
  - Connection to external MySQL database for client data

## Architecture

The system follows a clean, modular architecture:

- **API Layer**: FastAPI endpoints for authentication, admin operations, and verification
- **Service Layer**: Business logic for verification workflows
- **Agent Layer**: Specialized agents for different verification tasks
- **Integration Layer**: Integration with external APIs (Persona, Sift) and databases
- **Database Layer**: PostgreSQL for application data, MySQL for client data

## Database Architecture

This system uses a dual-database approach:

1. **Main PostgreSQL Database**: Stores all application data including:
   - User accounts and API keys
   - Verification records and results
   - Agent results and analysis
   
2. **External MySQL Database**: Contains client data that is used for verification:
   - User personal information
   - Business information and UBO data
   - Banking and transaction history
   - Login and activity history
   - Persona verification requests
   - Sift fraud scores

The system connects to the external MySQL database only when needed to fetch relevant data and never writes to it.

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL
- MySQL (client's database)
- AWS account with Bedrock access

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/your-org/verification-system.git
   cd verification-system
   ```

2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```
   pip install poetry
   poetry install
   ```

4. Create a `.env` file from the example:
   ```
   cp .env.example .env
   # Edit .env with your settings
   ```

5. Create the main database:
   ```
   psql -U postgres -c "CREATE DATABASE verification_system"
   ```

6. Apply migrations:
   ```
   alembic upgrade head
   ```

7. Run the application:
   ```
   uvicorn app.main:app --reload
   ```

### Docker Setup

1. Build and run with Docker Compose:
   ```
   docker-compose up -d --build
   ```

2. Initialize the external database (for development/testing only):
   ```
   docker-compose exec app bash scripts/init_external_db.sh
   ```

3. Access the API at http://localhost:8000/api/docs

## API Endpoints

### Authentication
- `POST /api/auth/login`: User login
- `POST /api/auth/token`: OAuth2 token endpoint
- `POST /api/auth/refresh`: Refresh token

### Admin
- `GET /api/admin/apikeys`: List API keys
- `POST /api/admin/apikeys`: Create API key
- `PUT /api/admin/apikeys/{key_id}`: Update API key
- `DELETE /api/admin/apikeys/{key_id}`: Delete API key

### Verification
- `POST /api/verify/kyc`: Start KYC verification
- `POST /api/verify/business`: Start business verification
- `GET /api/verify/status/{verification_id}`: Get verification status
- `GET /api/verify/report`: Get verification report

## Verification Workflows

### KYC Workflow

1. **User uploads user_id via /api/verify/kyc endpoint**
2. **Data Acquisition Agent**:
   - Connects to external MySQL database to fetch user data
   - Retrieves Persona inquiry ID from persona_verification_requests table
   - Gets Sift scores from sift_scores table
   - Fetches ID verification data from Persona
   - Stores all data for verification

3. **KYC Verification Agents (run in parallel)**:
   - Analyze user data and perform verification checks
   - Store verification results in the main PostgreSQL database

4. **Result Compilation**:
   - Analyzes results from all agents
   - Provides final verification decision
   - Stores comprehensive report

### KYB Workflow

1. **User uploads business_id via /api/verify/business endpoint**
2. **Data Acquisition Agent**:
   - Connects to external MySQL database to fetch business data from user_kyb_records
   - Retrieves UBO information from business_owners table
   - For each UBO, fetches personal data for KYC verification
   - Stores all data for verification

3. **UBO Verification**:
   - For each UBO, starts a separate KYC verification process
   - Stores references to UBO verifications

4. **Business Verification**:
   - Runs KYB verification agents in parallel
   - Waits for all UBO verifications to complete
   - Compiles comprehensive report including business and UBO verification results

## External Database Tables

The system interacts with the following tables in the external MySQL database:

1. **users**: Basic user information
2. **persona_verification_requests**: Persona verification inquiry IDs
3. **user_kyb_records**: Business information
4. **business_owners**: UBO information
5. **sift_scores**: Fraud detection scores
6. **bank_accounts**: User bank accounts
7. **bank_transactions**: Transaction history
8. **user_login_activities**: Login history
9. **business_verifications**: Business verification status

## License

MIT