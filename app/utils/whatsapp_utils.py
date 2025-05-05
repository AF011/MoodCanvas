# app/utils/whatsapp_utils.py
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime
import os
from dotenv import load_dotenv

# Import from existing db_utils to reuse connection
from app.utils.db_utils import client, db

# Create a new collection for WhatsApp mappings
whatsapp_mappings_collection = db.whatsapp_mappings

def register_whatsapp_number(phone_number, user_id, email, name):
    """Register a WhatsApp number to a user account in the database"""
    # Check if mapping already exists
    existing = whatsapp_mappings_collection.find_one({"phone_number": phone_number})
    if existing:
        # Update existing mapping
        whatsapp_mappings_collection.update_one(
            {"phone_number": phone_number},
            {
                "$set": {
                    "user_id": ObjectId(user_id),
                    "email": email,
                    "name": name,
                    "updated_at": datetime.datetime.now()
                }
            }
        )
    else:
        # Create new mapping
        mapping = {
            "phone_number": phone_number,
            "user_id": ObjectId(user_id),
            "email": email,
            "name": name,
            "created_at": datetime.datetime.now(),
            "updated_at": datetime.datetime.now(),
            "active": True
        }
        whatsapp_mappings_collection.insert_one(mapping)
    
    return True

def unregister_whatsapp_number(phone_number):
    """Deactivate a WhatsApp mapping"""
    result = whatsapp_mappings_collection.update_one(
        {"phone_number": phone_number},
        {
            "$set": {
                "active": False,
                "updated_at": datetime.datetime.now()
            }
        }
    )
    return result.modified_count > 0

def get_user_by_whatsapp(phone_number):
    """Get user data from a WhatsApp number"""
    mapping = whatsapp_mappings_collection.find_one(
        {"phone_number": phone_number, "active": True}
    )
    return mapping

def get_whatsapp_numbers_for_user(user_id):
    """Get all WhatsApp numbers registered to a user"""
    mappings = whatsapp_mappings_collection.find(
        {"user_id": ObjectId(user_id), "active": True}
    )
    return [m["phone_number"] for m in mappings]

def log_whatsapp_interaction(phone_number, user_id, user_message, alter_ego_response):
    """Log a WhatsApp interaction for analytics"""
    log = {
        "phone_number": phone_number,
        "user_id": ObjectId(user_id),
        "user_message": user_message,
        "alter_ego_response": alter_ego_response,
        "timestamp": datetime.datetime.now()
    }
    db.whatsapp_logs.insert_one(log)