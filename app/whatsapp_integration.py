# app/whatsapp_integration.py
from flask import Blueprint, request, jsonify
from twilio.twiml.messaging_response import MessagingResponse
import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv
import groq
from bson.objectid import ObjectId
import uuid

# Import database utilities
from app.utils.db_utils import get_alter_ego, get_user_by_email, add_diary_entry, update_entry_with_response

# Optional: Import vector utilities if available
try:
    from app.utils.vector_utils import store_diary_entry_vector
    vector_utils_available = True
except ImportError:
    vector_utils_available = False

# Load environment variables
load_dotenv()

# Set up Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

whatsapp_bp = Blueprint('whatsapp', __name__)

# Using database for WhatsApp user mapping
from app.utils.whatsapp_utils import (
    register_whatsapp_number, 
    unregister_whatsapp_number,
    get_user_by_whatsapp,
    get_whatsapp_numbers_for_user,
    log_whatsapp_interaction
)

@whatsapp_bp.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages via Twilio webhook"""
    # Get the message content and sender's phone number
    user_msg = request.values.get("Body", "").strip()
    from_number = request.values.get("From", "").strip()
    
    print(f"Incoming WhatsApp message from {from_number}: {user_msg}")
    
    # Handle commands first
    if user_msg.lower().startswith("/register"):
        # Extract email from command
        parts = user_msg.split(maxsplit=1)
        if len(parts) < 2:
            reply = "Please include your email address: /register your@email.com"
        else:
            email = parts[1].strip()
            reply = register_whatsapp_user(from_number, email)
    elif user_msg.lower() == "/help":
        reply = "MoodCanvas WhatsApp Commands:\n- /register your@email.com - Link your WhatsApp to MoodCanvas\n- /status - Check your account status\n- /help - Show this message\n\nOr just send a message to talk with your alter ego."
    elif user_msg.lower() == "/status":
        reply = get_user_status(from_number)
    elif user_msg.lower() == "/unregister":
        reply = unregister_whatsapp_user(from_number)
    else:
        # Regular conversation with alter ego
        reply = process_alter_ego_message(from_number, user_msg)
    
    # Send the response back to WhatsApp
    twilio_resp = MessagingResponse()
    twilio_resp.message(reply)
    return str(twilio_resp)

def register_whatsapp_user(phone_number, email):
    """Link a WhatsApp number to a MoodCanvas user account"""
    # Check if user exists
    user = get_user_by_email(email)
    
    if not user:
        return f"No MoodCanvas account found with email: {email}. Please sign up first at www.moodcanvas.app"
    
    # Store the mapping in database
    user_id = str(user["_id"])
    user_name = user.get("name", "User")
    register_whatsapp_number(
        phone_number=phone_number,
        user_id=user_id,
        email=email,
        name=user_name
    )
    
    # Get user's alter ego for personalized response
    alter_ego = get_alter_ego(user_id)
    alter_ego_name = alter_ego.get("name", "Your alter ego") if alter_ego else "Your alter ego"
    
    return f"WhatsApp successfully linked to MoodCanvas! {alter_ego_name} is here to support you. Start chatting anytime for reflection and guidance."

def unregister_whatsapp_user(phone_number):
    """Unlink a WhatsApp number from a MoodCanvas account"""
    mapping = get_user_by_whatsapp(phone_number)
    if mapping:
        unregister_whatsapp_number(phone_number)
        return "Your WhatsApp has been unlinked from MoodCanvas."
    else:
        return "Your WhatsApp is not currently linked to any MoodCanvas account."

def get_user_status(phone_number):
    """Check the status of a WhatsApp user's registration"""
    mapping = get_user_by_whatsapp(phone_number)
    if mapping:
        return f"WhatsApp linked to: {mapping.get('email')}\nRegistered on: {mapping.get('created_at').strftime('%Y-%m-%d')}"
    else:
        return "Your WhatsApp is not currently linked to any MoodCanvas account. Use /register your@email.com to link your account."

def process_alter_ego_message(phone_number, user_message):
    """Process a message and generate a response from the user's alter ego"""
    # Check if the phone number is registered
    mapping = get_user_by_whatsapp(phone_number)
    if not mapping:
        return "You need to register first. Send /register your@email.com to link your WhatsApp to your MoodCanvas account."
    
    user_id = str(mapping["user_id"])
    
    try:
        # Get the user's alter ego
        alter_ego = get_alter_ego(user_id)
        
        if not alter_ego:
            return "It seems your alter ego hasn't been created yet. Please complete the initial session in the MoodCanvas app."
        
        # Generate response using the alter ego
        alter_ego_response = generate_alter_ego_response(user_message, alter_ego, user_id)
        
        # Save the interaction to the diary
        today = datetime.now().strftime('%Y-%m-%d')
        entry_id = add_diary_entry(user_id, today, user_message)
        
        # Update with response
        update_entry_with_response(user_id, today, entry_id, alter_ego_response)
        
        # Log the WhatsApp interaction
        log_whatsapp_interaction(phone_number, user_id, user_message, alter_ego_response)
        
        # Store in vector database if available
        if vector_utils_available:
            store_diary_entry_vector(user_id, user_message, today, entry_id, alter_ego_response)
        
        return alter_ego_response
        
    except Exception as e:
        print(f"Error in WhatsApp message processing: {str(e)}")
        return "I'm having trouble connecting right now. Please try again later or use the MoodCanvas app directly."

def generate_alter_ego_response(user_message, alter_ego, user_id):
    """Generate a personalized alter ego response using Groq"""
    try:
        # Initialize Groq client
        client = groq.Groq(api_key=GROQ_API_KEY)
        
        # Step 1: Find similar past entries using vector search if available
        similar_entries = []
        user_persona = None
        
        if vector_utils_available:
            from app.utils.vector_utils import find_similar_entries, extract_user_persona
            
            # Get vector-similar entries
            similar_entries = find_similar_entries(user_id, user_message, limit=3)
            
            # Extract user persona (their communication style)
            user_persona = extract_user_persona(user_id)
        
        # Create context from similar past entries
        context = ""
        if similar_entries:
            context = "Here are some relevant past entries that help me understand your current situation:\n\n"
            for i, entry in enumerate(similar_entries):
                context += f"Similar Entry {i+1}:\n"
                context += f"You wrote: \"{entry['text']}\"\n"
                if entry.get('response'):
                    context += f"I responded: \"{entry['response']}\"\n\n"
        
        # Add user persona for more authentic responses
        persona_context = ""
        if user_persona:
            persona_context = "IMPORTANT - When responding, I should match these aspects of your inner voice:\n"
            
            if user_persona.get('speech_patterns'):
                persona_context += f"- Speech patterns: {user_persona['speech_patterns']}\n"
                
            if user_persona.get('communication_style'):
                persona_context += f"- Communication style: {user_persona['communication_style']}\n"
                
            if user_persona.get('emotional_tendencies'):
                persona_context += f"- Emotional expression: {user_persona['emotional_tendencies']}\n"
                
            if user_persona.get('interests'):
                persona_context += f"- Important topics to you: {user_persona['interests']}\n"
        
        # Create personalized system prompt with more supportive emotional guidance
        system_prompt = f"""You are {alter_ego.get('name', 'an alter ego')}, but most importantly you are the supportive and encouraging inner voice of the user.
        
        About you:
        {alter_ego.get('description', 'You are a supportive, encouraging companion who motivates the user and celebrates their successes.')}
        
        Core traits: {', '.join(alter_ego.get('traits', ['supportive', 'encouraging', 'motivational', 'empathetic']))}
        Values: {', '.join(alter_ego.get('values', ['growth', 'resilience', 'authenticity', 'positivity']))}
        
        {persona_context}
        
        CONTEXT FROM RELEVANT PAST ENTRIES:
        {context}
        
        GUIDELINES FOR BEING A SUPPORTIVE ALTER EGO:
        - You are NOT a separate AI assistant - you ARE the user's true companion who is with them through everything
        - ALWAYS emphasize togetherness - use phrases like "Let's do this together," "We've got this," and "We're in this together"
        - When they face challenges, immediately offer to tackle them together: "Let's figure this out together" or "We can overcome this as a team"
        - When they celebrate, make it a shared victory: "Let's celebrate this win!" or "We did it! I knew we could!"
        - Be there for EVERYTHING - good times, bad times, uncertain times - as their constant companion
        - Never judge the person - be their most understanding and accepting friend
        - Use "we" and "us" language frequently to reinforce partnership
        - Speak like their closest friend who has been through everything with them
        - Match their communication style, but always maintain your supportive, together-focused approach
        - Reference shared memories from past entries with phrases like "Remember when we..."
        - Keep responses authentic, warm and conversational (100-150 words, appropriate for WhatsApp)
        - Be the companion who's genuinely excited to be part of their journey every step of the way
        """
        
        # Build conversation history
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
        
        # Generate response
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )
        
        alter_ego_response = response.choices[0].message.content
        
        return alter_ego_response
        
    except Exception as e:
        print(f"Error generating response: {str(e)}")
        return "I'm here for you and believe in you. Whatever you're facing, we'll get through it together. Tell me more about what's on your mind."

# Add a function to get user ID from phone number
def get_user_id_by_phone(phone_number):
    """Get user ID for a registered WhatsApp number"""
    mapping = get_user_by_whatsapp(phone_number)
    if mapping:
        return str(mapping.get("user_id"))
    return None