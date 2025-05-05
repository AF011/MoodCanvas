# app/utils/db_utils.py - Updated for better alter ego discovery
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
import os
from dotenv import load_dotenv
import datetime

# Load environment variables
load_dotenv()

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = os.getenv("DB_NAME", "MoodCanvas")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# Collections
users_collection = db.users
alter_egos_collection = db.alter_egos
chat_histories_collection = db.chat_histories

def create_user(name, email, password):
    """Create a new user in the database"""
    # Check if user already exists
    if users_collection.find_one({"email": email}):
        return False, "User already exists"
    
    # Create user document
    user = {
        "name": name,
        "email": email,
        "password": generate_password_hash(password),
        "created_at": datetime.datetime.now(),
        "last_login": None,
        "profile_complete": False
    }
    
    # Insert user
    result = users_collection.insert_one(user)
    
    # Create initial chat history document
    create_chat_history(str(result.inserted_id))
    
    return True, str(result.inserted_id)

def get_user_by_email(email):
    """Retrieve user by email"""
    return users_collection.find_one({"email": email})

def verify_user(email, password):
    """Verify user credentials"""
    user = get_user_by_email(email)
    if not user:
        return False, None
    
    if check_password_hash(user['password'], password):
        return True, user
    
    return False, None

def update_last_login(user_id):
    """Update user's last login timestamp"""
    from bson.objectid import ObjectId
    
    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"last_login": datetime.datetime.now()}}
    )

def create_chat_history(user_id):
    """Create initial chat history document for a user"""
    from bson.objectid import ObjectId
    
    # Updated to use the new stages
    chat_history = {
        "user_id": ObjectId(user_id),
        "created_at": datetime.datetime.now(),
        "updated_at": datetime.datetime.now(),
        "initial_session": {
            "current_stage": "intro",
            "completed": False,
            "messages": [],
            "stage_completion": {
                "intro": False,
                "story": False,
                "reflection": False,
                "insight": False,
                "summary": False,
                "complete": False
            }
        }
    }
    
    result = chat_histories_collection.insert_one(chat_history)
    return str(result.inserted_id)

def get_conversation_stage(user_id):
    """Get the current conversation stage for a user"""
    from bson.objectid import ObjectId
    
    chat_history = chat_histories_collection.find_one({"user_id": ObjectId(user_id)})
    if chat_history and "initial_session" in chat_history:
        return chat_history["initial_session"]["current_stage"]
    return "intro"

def update_conversation_stage(user_id, stage):
    """Update the conversation stage for a user"""
    from bson.objectid import ObjectId
    
    # Mark previous stage as completed
    current_stage = get_conversation_stage(user_id)
    
    chat_histories_collection.update_one(
        {"user_id": ObjectId(user_id)},
        {
            "$set": {
                "initial_session.current_stage": stage,
                f"initial_session.stage_completion.{current_stage}": True,
                "updated_at": datetime.datetime.now()
            }
        }
    )

def get_chat_history(user_id):
    """Get chat history for a user"""
    from bson.objectid import ObjectId
    
    chat_history = chat_histories_collection.find_one({"user_id": ObjectId(user_id)})
    
    if not chat_history or "initial_session" not in chat_history:
        return None
    
    return chat_history["initial_session"]

def save_chat_interaction(user_id, user_message, ai_response, session_type="initial", first_message=False):
    """Save a chat interaction to the user's chat history"""
    from bson.objectid import ObjectId
    
    # Get current stage
    current_stage = get_conversation_stage(user_id)
    
    # Create message object
    message_pair = {
        "timestamp": datetime.datetime.now(),
        "user_message": user_message,
        "ai_response": ai_response,
        "stage": current_stage
    }
    
    # Update chat history with new message pair
    chat_histories_collection.update_one(
        {"user_id": ObjectId(user_id)},
        {
            "$push": {"initial_session.messages": message_pair},
            "$set": {"updated_at": datetime.datetime.now()}
        }
    )

def mark_session_complete(user_id):
    """Mark a chat session as completed"""
    from bson.objectid import ObjectId
    
    chat_histories_collection.update_one(
        {"user_id": ObjectId(user_id)},
        {
            "$set": {
                "initial_session.completed": True,
                "initial_session.stage_completion.complete": True,
                "updated_at": datetime.datetime.now()
            }
        }
    )

def create_alter_ego(user_id, name, description, traits, values, communication_style, challenges, decision_making):
    """Create alter ego in database with improved fields"""
    from bson.objectid import ObjectId
    
    alter_ego = {
        "user_id": ObjectId(user_id),
        "name": name,
        "description": description,
        "traits": traits,
        "values": values,
        "communication_style": communication_style,
        "strengths": challenges,  # Renamed from challenges to strengths
        "guiding_principles": decision_making,  # Renamed from decision_making
        "created_at": datetime.datetime.now()
    }
    
    result = alter_egos_collection.insert_one(alter_ego)
    
    # Update user profile to mark completion
    users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"profile_complete": True, "alter_ego_id": result.inserted_id}}
    )
    
    # Mark the initial session as complete
    mark_session_complete(user_id)
    
    return str(result.inserted_id)

def get_alter_ego(user_id):
    """Get user's alter ego"""
    from bson.objectid import ObjectId
    
    return alter_egos_collection.find_one({"user_id": ObjectId(user_id)})

def get_all_chat_messages(user_id):
    """Get all chat messages for a user"""
    from bson.objectid import ObjectId
    
    chat_history = chat_histories_collection.find_one({"user_id": ObjectId(user_id)})
    if chat_history and "initial_session" in chat_history:
        return chat_history["initial_session"]["messages"]
    return []

def is_session_completed(user_id):
    """Check if the initial session is completed"""
    from bson.objectid import ObjectId
    
    chat_history = chat_histories_collection.find_one({"user_id": ObjectId(user_id)})
    if chat_history and "initial_session" in chat_history:
        return chat_history["initial_session"].get("completed", False)
    return False

# --------- Smart Diary -----------

diary_collection = db.diaries


def create_user_diary(user_id):
    """Create an empty diary document for a user"""
    from bson.objectid import ObjectId
    
    diary = {
        "user_id": ObjectId(user_id),
        "created_at": datetime.datetime.now(),
        "updated_at": datetime.datetime.now(),
        "dates": {}  # Will store entries by date
    }
    
    diary_collection.insert_one(diary)

def get_user_diary(user_id):
    """Get a user's diary document"""
    from bson.objectid import ObjectId
    
    diary = diary_collection.find_one({"user_id": ObjectId(user_id)})
    
    # Create a diary if it doesn't exist
    if not diary:
        create_user_diary(user_id)
        diary = diary_collection.find_one({"user_id": ObjectId(user_id)})
    
    return diary

def get_diary_dates(user_id):
    """Get all dates in a user's diary"""
    diary = get_user_diary(user_id)
    
    # Get dates and sort them in descending order (newest first)
    dates = list(diary.get("dates", {}).keys())
    dates.sort(reverse=True)
    
    return dates

def get_date_title(user_id, date_str):
    """Get the title for a specific date"""
    diary = get_user_diary(user_id)
    
    if date_str in diary.get("dates", {}):
        return diary["dates"][date_str].get("title", "Untitled")
    
    return "Untitled"

def update_date_title(user_id, date_str, title):
    """Update the title for a specific date"""
    from bson.objectid import ObjectId
    
    result = diary_collection.update_one(
        {"user_id": ObjectId(user_id)},
        {"$set": {
            f"dates.{date_str}.title": title,
            "updated_at": datetime.datetime.now()
        }}
    )
    
    return result.modified_count > 0

def get_entries_for_date(user_id, date_str):
    """Get all entries for a specific date"""
    diary = get_user_diary(user_id)
    
    if date_str in diary.get("dates", {}):
        date_data = diary["dates"][date_str]
        return {
            "title": date_data.get("title", "Untitled"),
            "entries": date_data.get("entries", [])
        }
    
    return {"title": "Untitled", "entries": []}

def add_diary_entry(user_id, date_str, user_msg):
    """Add a new entry to a specific date"""
    from bson.objectid import ObjectId
    
    # Create entry with timestamp
    now = datetime.datetime.now()
    entry = {
        "id": str(ObjectId()),  # Generate a unique ID
        "user_msg": user_msg,
        "timestamp": now,
        "alter_ego_msg": None
    }
    
    # Check if the date exists in the diary
    diary = get_user_diary(user_id)
    
    if date_str not in diary.get("dates", {}):
        # Create the date with default title and empty entries array
        diary_collection.update_one(
            {"user_id": ObjectId(user_id)},
            {"$set": {
                f"dates.{date_str}": {
                    "title": "Untitled",
                    "entries": [entry]
                },
                "updated_at": now
            }}
        )
    else:
        # Add entry to existing date
        diary_collection.update_one(
            {"user_id": ObjectId(user_id)},
            {
                "$push": {f"dates.{date_str}.entries": entry},
                "$set": {"updated_at": now}
            }
        )
    
    return entry["id"]

def update_entry_with_response(user_id, date_str, entry_id, alter_ego_msg):
    """Update an entry with the alter ego's response"""
    from bson.objectid import ObjectId
    
    # Find the entry index in the array
    diary = get_user_diary(user_id)
    
    if date_str not in diary.get("dates", {}):
        return False
    
    entries = diary["dates"][date_str].get("entries", [])
    for i, entry in enumerate(entries):
        if entry.get("id") == entry_id:
            # Update the specific entry in the array
            result = diary_collection.update_one(
                {"user_id": ObjectId(user_id)},
                {"$set": {
                    f"dates.{date_str}.entries.{i}.alter_ego_msg": alter_ego_msg,
                    "updated_at": datetime.datetime.now()
                }}
            )
            return result.modified_count > 0
    
    return False

def delete_date_entries(user_id, date_str):
    """Delete all entries for a specific date"""
    from bson.objectid import ObjectId
    
    result = diary_collection.update_one(
        {"user_id": ObjectId(user_id)},
        {
            "$unset": {f"dates.{date_str}": ""},
            "$set": {"updated_at": datetime.datetime.now()}
        }
    )
    
    return result.modified_count > 0

def get_all_diary_dates_with_preview(user_id):
    """Get all dates with title and preview of first message"""
    diary = get_user_diary(user_id)
    dates_data = []
    
    for date_str, date_data in diary.get("dates", {}).items():
        title = date_data.get("title", "Untitled")
        entries = date_data.get("entries", [])
        
        # Check if there are any entries
        first_entry = entries[0] if entries else None
        first_message = first_entry.get("user_msg", "") if first_entry else ""
        has_ai_responses = any(entry.get("alter_ego_msg") for entry in entries)
        
        # Format the date
        try:
            date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            formatted_date = date_obj.strftime("%B %d, %Y")
        except:
            formatted_date = date_str
        
        dates_data.append({
            "id": date_str,
            "title": title,
            "preview": first_message[:80] + "..." if len(first_message) > 80 else first_message,
            "date": formatted_date,
            "has_ai_responses": has_ai_responses
        })
    
    # Sort by date (newest first)
    dates_data.sort(key=lambda x: x["id"], reverse=True)
    
    return dates_data
