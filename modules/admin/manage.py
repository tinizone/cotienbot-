from fastapi import Depends, HTTPException
from database.firestore import FirestoreClient

async def admin_only(user_id: str):
    db = FirestoreClient()
    user = db.get_user(user_id)
    if not user.exists or user.to_dict().get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user.to_dict()
