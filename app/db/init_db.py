import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import Base, engine
from app.models.user import User
from app.utils.logging import get_logger

logger = get_logger("init_db")


async def create_first_admin(db: AsyncSession) -> None:
    try:
        # Check if admin exists
        result = await db.execute(
           text("SELECT * FROM users WHERE email = :email"),
            {"email": settings.FIRST_ADMIN_EMAIL}
        )
        user = result.first()
        logger.info("user data")
        
        # Add this check before iterating
        if user:
            for row in user:
                logger.info(row)
                
        if not user:
            # Create admin user
            admin = User(
                email=settings.FIRST_ADMIN_EMAIL,
                hashed_password=get_password_hash(settings.FIRST_ADMIN_PASSWORD),
                is_active=True,
                is_admin=True
            )
            db.add(admin)
            await db.commit()
            logger.info("Created first admin user")
        else:
            logger.info("Admin user already exists")
    except Exception as e:
        logger.error(f"Error creating first admin user: {str(e)}")
        await db.rollback()
        raise


async def init_db(db: AsyncSession) -> None:
    """
    Initialize database
    
    Args:
        db: Database session
    """
    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        # Create first admin user
        await create_first_admin(db)
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise