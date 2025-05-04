# UPDATE: /modules/admin/manage.py
from fastapi import Depends, HTTPException
from database.firestore import FirestoreClient
import logging

logger = logging.getLogger(__name__)

def get_db():
    """Dependency for FirestoreClient."""
    return FirestoreClient()

async def admin_only(user_id: str, db: FirestoreClient = Depends(get_db)):
    """Ensure the user is an admin."""
    try:
        user = db.get_user(user_id)
        if not user:
            logger.warning(f"User {user_id} not found for admin check")
            raise HTTPException(status_code=404, detail="User not found")
        if user.get("role") != "admin":
            logger.warning(f"User {user_id} is not an admin")
            raise HTTPException(status_code=403, detail="Admin only")
        logger.info(f"Admin check passed for user {user_id}")
        return user
    except Exception as e:
        logger.error(f"Error in admin check for user {user_id}: {str(e)}")
        raise
