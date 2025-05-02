# File: /modules/admin/manage.py
from fastapi import Depends, HTTPException
from database.firestore import FirestoreClient

db = FirestoreClient()

async def admin_only(user_id: str):
    user = db.get_user(user_id)
    if not user or user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    return user
