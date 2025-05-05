# app/routes.py - Updated Initial Session Routes
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from app.utils.db_utils import (
    create_user, verify_user, update_last_login, create_alter_ego, save_chat_interaction,
    get_chat_history, get_conversation_stage, update_conversation_stage, 
    is_session_completed, get_all_chat_messages, get_alter_ego, users_collection, create_chat_history,
    get_alter_ego
)
from app.utils.db_utils import (
    get_user_diary, get_diary_dates, get_entries_for_date, add_diary_entry,
    update_entry_with_response, delete_date_entries, get_all_diary_dates_with_preview,
    get_alter_ego, update_date_title
)
from bson.objectid import ObjectId
import json
import requests
import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
import groq
from groq import Groq

# Load environment variables
load_dotenv()

# Set up Groq API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

auth_bp = Blueprint('auth', __name__)
initial_session_bp = Blueprint('initial_session', __name__)
dashboard_bp = Blueprint('dashboard', __name__)
mood_canvas_bp = Blueprint('mood_canvas', __name__)
profile_bp = Blueprint('profile', __name__)

# ------------------ Authentication Routes ------------------
@auth_bp.route('/')
def index():
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        success, user = verify_user(email, password)
        
        if success:
            # Store user info in session
            session['user_id'] = str(user['_id'])
            session['name'] = user['name']
            session['email'] = user['email']
            
            # Update last login
            update_last_login(session['user_id'])
            
            # Check if profile is complete
            if user.get('profile_complete', False):
                return redirect(url_for('dashboard.index'))
            else:
                return redirect(url_for('initial_session.index'))
        else:
            flash('Invalid email or password')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        
        if not name or not email or not password:
            flash('All fields are required')
            return render_template('auth/register.html')
        
        success, message = create_user(name, email, password)
        
        if success:
            flash('Account created successfully! Please login.')
            return redirect(url_for('auth.login'))
        else:
            flash(message)
    
    return render_template('auth/register.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

# ------------------ Initial Session Routes ------------------
@initial_session_bp.route('/')
def index():
    """Render the initial AI interaction page"""
    # Check if user is logged in
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    user_name = session.get('name', '')
    
    # Get user data
    user_data = users_collection.find_one({"_id": ObjectId(user_id)})
    
    # If user profile is already complete, redirect to dashboard
    if user_data and user_data.get('profile_complete', False):
        return redirect(url_for('dashboard.index'))
    
    # Get chat history
    chat_history = get_chat_history(user_id)
    
    # Initialize if not exists
    if not chat_history:
        create_chat_history(user_id)
        chat_history = get_chat_history(user_id)
    
    # Store conversation stage in session
    session['conversation_stage'] = get_conversation_stage(user_id)
    
    # Format messages for frontend display
    formatted_messages = []
    if chat_history and 'messages' in chat_history:
        for msg in chat_history['messages']:
            formatted_messages.append({
                'sender': 'user',
                'content': msg.get('user_message', ''),
                'timestamp': msg.get('timestamp', datetime.now()).isoformat()
            })
            formatted_messages.append({
                'sender': 'ai',
                'content': msg.get('ai_response', ''),
                'timestamp': msg.get('timestamp', datetime.now()).isoformat()
            })
    
    # Check if we need to send a welcome message (for new sessions)
    send_welcome = len(formatted_messages) == 0
    
    return render_template('initial_session/index.html', 
                          user_name=user_name,
                          user_id=user_id,
                          chat_history=formatted_messages,
                          send_welcome=send_welcome,
                          current_stage=session['conversation_stage'])

@initial_session_bp.route('/chat', methods=['POST'])
def chat():
    """Handle chat API requests"""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session['user_id']
    user_name = session.get('name', '')
    
    data = request.json
    user_message = data.get('message', '')
    welcome_message = data.get('welcome', False)
    
    if welcome_message:
        # Check if session is already completed
        if is_session_completed(user_id):
            alter_ego = get_alter_ego(user_id)
            if alter_ego:
                return jsonify({
                    "response": f"Welcome back, {user_name}! Your alter ego {alter_ego.get('name')} is ready to guide you through your emotional journey.",
                    "is_complete": True,
                    "alter_ego": {
                        "name": alter_ego.get('name'),
                        "description": alter_ego.get('description')
                    }
                })
        
        # Get current stage 
        current_stage = get_conversation_stage(user_id)
        
        # Get message count to check if we're starting fresh or continuing
        messages = get_all_chat_messages(user_id)
        
        if not messages:
            # Brand new session, send personalized welcome
            welcome_response = f"Hello {user_name}, I'm Lumina. I'm here to help you discover your inner Alter Ego - the authentic self that drives your actions and decisions. To start, I'd love to get to know you better. How old are you, and what are your main interests or passions?"
            
            # Save this as first AI message
            save_chat_interaction(user_id, "", welcome_response, first_message=True)
            
            return jsonify({
                "response": welcome_response,
                "is_complete": False,
                "stage": current_stage,
                "alter_ego": None
            })
        else:
            # Continuing existing session, return last AI message
            last_message = messages[-1]
            return jsonify({
                "response": last_message.get('ai_response', "Let's continue our conversation about discovering your inner Alter Ego. What would you like to share about yourself?"),
                "is_complete": False,
                "stage": current_stage,
                "alter_ego": None
            })
    
    # Regular message handling
    # Check if session is already completed
    if is_session_completed(user_id):
        alter_ego = get_alter_ego(user_id)
        if alter_ego:
            return jsonify({
                "response": f"Your alter ego {alter_ego.get('name')} is here to guide you. {alter_ego.get('description')}",
                "is_complete": True,
                "alter_ego": {
                    "name": alter_ego.get('name'),
                    "description": alter_ego.get('description')
                }
            })
    
    # Handle empty messages
    if not user_message:
        return jsonify({"error": "Empty message"}), 400
    
    try:
        # Get current stage - from database, not session to ensure consistency
        current_stage = get_conversation_stage(user_id)
        
        # Update session with current stage to keep in sync
        session['conversation_stage'] = current_stage
        
        # Get conversation history
        messages = get_all_chat_messages(user_id)
        conversation_history = []
        
        # Format conversation history for the AI
        for msg in messages:
            if msg.get('user_message'):  # Skip empty user messages (like first welcome)
                conversation_history.append({"role": "user", "content": msg.get('user_message', '')})
            conversation_history.append({"role": "assistant", "content": msg.get('ai_response', '')})
        
        # Add current user message
        conversation_history.append({"role": "user", "content": user_message})
        
        # Process with Groq
        system_prompt = get_alter_ego_system_prompt(current_stage, user_name)
        ai_response = process_with_groq(system_prompt, conversation_history)
        
        # Save interaction to database
        save_chat_interaction(user_id, user_message, ai_response)
        
        # Determine if we should move to the next stage
        next_stage = determine_next_stage(user_id, current_stage, user_message, ai_response)
        
        # Update stage if needed
        if next_stage != current_stage:
            update_conversation_stage(user_id, next_stage)
            session['conversation_stage'] = next_stage
        
        # Check if conversation is complete
        is_complete = next_stage == 'complete'
        
        # Create alter ego if session is complete
        alter_ego_data = None
        if is_complete:
            # Get full conversation history for analysis
            full_history = get_all_chat_messages(user_id)
            alter_ego_data = create_user_alter_ego(full_history, user_id, user_name)
        
        return jsonify({
            "response": ai_response,
            "is_complete": is_complete,
            "stage": next_stage,
            "alter_ego": alter_ego_data
        })
    
    except Exception as e:
        print(f"Error in AI processing: {str(e)}")
        return jsonify({"error": "Failed to process message"}), 500

def get_alter_ego_system_prompt(stage, user_name):
    """Get the improved alter ego system prompt based on conversation stage"""
    base_prompt = f"""You are Lumina, a guide who helps {user_name} discover their inner Alter Ego - their authentic inner self.

Your goal is to have a natural, meaningful conversation that helps the user understand their inner strengths and abilities.

Your approach:
- Be warm, friendly and genuinely interested in the user
- Ask straightforward, simple questions about their life, interests, and self-perception
- Focus on understanding their age, interests, passions, and how they see themselves
- Help them discover their inner abilities and strengths
- AVOID getting stuck in lengthy discussions about a single topic like coding
- Keep the conversation balanced and flowing naturally

IMPORTANT GUIDELINES:
- Ask direct questions like "How old are you?" or "What are you passionate about?"
- If they mention a hobby like coding, acknowledge it briefly but don't fixate on it
- Ask about different aspects of their life to build a complete picture
- Focus on self-belief, inner confidence, and how they perceive themselves
- Keep your responses concise and engaging
- NEVER use psychological terminology or test-like language
"""

    stage_prompts = {
        'intro': f"""
{base_prompt}

You're beginning your conversation with {user_name}. Start by warmly introducing yourself as Lumina.

Then ask direct questions to understand the basics about them:
- Ask about their age
- Ask about their interests and passions
- Ask how they spend their time

Example introduction:
"Hello {user_name}, I'm Lumina. I'm here to help you discover your inner Alter Ego - the authentic self that drives your actions and decisions. To start, I'd love to get to know you better. How old are you, and what are your main interests or passions?"
""",
        
        'personal': f"""
{base_prompt}

Now that you have some basic information about {user_name}, explore their self-perception:
- Ask how they see themselves (strengths, weaknesses)
- Ask about moments when they feel most confident
- Ask about situations where they struggle
- Ask about their dreams and aspirations

Focus on understanding how they view themselves and what they believe they're capable of.
""",
        
        'confidence': f"""
{base_prompt}

Based on what you've learned so far, explore {user_name}'s confidence and inner beliefs:
- Ask about times when they felt particularly strong or capable
- Ask how they handle challenges or setbacks
- Ask what they believe is their greatest strength
- Ask what holds them back from being their best self

The goal is to understand their level of self-belief and inner confidence.
""",
        
        'values': f"""
{base_prompt}

Now explore {user_name}'s core values and principles:
- Ask what matters most to them in life
- Ask about their definition of success
- Ask about the impact they want to have on others
- Ask who they admire and why

Focus on understanding their guiding principles and what drives their decisions.
""",
        
        'insight': f"""
{base_prompt}

Based on your conversation so far, offer an insightful reflection on what you've observed about {user_name}:
- Highlight 2-3 key strengths you've noticed
- Mention how these strengths might serve them in different situations
- Acknowledge any inner conflicts or challenges they've shared
- Ask if your observations feel accurate to them

Then ask if there's anything else they'd like to share about themselves.
""",
        
        'summary': f"""
{base_prompt}

It's time to bring your conversation to a meaningful conclusion.

Synthesize what you've learned about {user_name} into a warm, affirming summary that:
- Acknowledges their unique strengths and qualities
- Highlights their inner abilities and potential
- Offers a positive reflection on how these qualities might serve them
- Feels personalized and specific to them

Ask if this reflection resonates with them and if there's anything they'd like to add.
""",
        
        'complete': f"""
{base_prompt}

Based on your conversation with {user_name}, create a meaningful Alter Ego that captures their authentic inner self.

Choose a powerful, symbolic name that reflects their essence (like "Leo", "Phoenix," "Nova," "Atlas," etc.)

Write a compelling description of this Alter Ego that:
- Captures their core strengths and inner abilities
- Reflects their values and what makes them unique
- Feels inspiring but authentic to who they are
- Emphasizes potential while acknowledging their real self

Tell them this Alter Ego represents their inner capabilities and will be their companion in the Mood Canvas journey.
"""
    }
    
    return stage_prompts.get(stage, stage_prompts['intro'])

def determine_next_stage(user_id, current_stage, user_message, ai_response):
    """Determine if we should move to the next stage based on improved conversation flow"""
    # Define the stage progression - updated to match our new approach
    stage_order = ['intro', 'personal', 'confidence', 'values', 'insight', 'summary', 'complete']
    
    # Get message count for current stage
    messages = get_all_chat_messages(user_id)
    current_stage_messages = [msg for msg in messages if msg.get("stage") == current_stage]
    
    # Count user messages only (to track proper exchanges)
    user_message_count = len([msg for msg in current_stage_messages if msg.get('user_message', '').strip()])
    
    # Define transition logic based on stages and meaningful exchanges
    if current_stage == 'intro' and user_message_count >= 3:
        # After getting basic info (age, interests, etc.), move to personal
        return 'personal'
    
    elif current_stage == 'personal' and user_message_count >= 3:
        # After exploring self-perception, move to confidence
        return 'confidence'
    
    elif current_stage == 'confidence' and user_message_count >= 3:
        # After discussing inner confidence, move to values
        return 'values'
    
    elif current_stage == 'values' and user_message_count >= 3:
        # After exploring values, provide insight
        return 'insight'
    
    elif current_stage == 'insight' and user_message_count >= 2:
        # After user responds to insights, move to summary
        return 'summary'
    
    elif current_stage == 'summary' and user_message_count >= 1:
        # After user confirms summary, complete the session
        return 'complete'
    
    # Additional intelligence: Check for very short responses
    if current_stage != 'complete' and len(user_message.split()) <= 3:
        # Count consecutive short responses
        short_response_count = 0
        for msg in reversed(current_stage_messages):
            if msg.get('user_message') and len(msg.get('user_message', '').split()) <= 3:
                short_response_count += 1
            else:
                break
            
        # If we get 3 consecutive very short responses, consider moving to next stage
        if short_response_count >= 3:
            current_index = stage_order.index(current_stage)
            if current_index < len(stage_order) - 1:
                return stage_order[current_index + 1]
    
    # Stay in current stage if conditions aren't met
    return current_stage

def process_with_groq(system_prompt, conversation_history):
    """Process a message with Groq API"""
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    # Format messages for API
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 800
    }
    
    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload
    )
    
    if response.status_code != 200:
        raise Exception(f"Groq API error: {response.text}")
    
    response_data = response.json()
    return response_data["choices"][0]["message"]["content"]

def create_user_alter_ego(conversation_history, user_id, user_name):
    """Create a meaningful alter ego based on conversation insights"""
    try:
        # Prepare analysis prompt
        analysis_prompt = f"""
        You are Lumina, a guide who helps people discover their inner Alter Ego.

        Based on your conversation with {user_name}, create a meaningful Alter Ego that represents their authentic inner self.
        
        Review the conversation carefully and identify:
        1. Their age and stage in life
        2. Their core interests and passions
        3. Their self-described strengths and abilities
        4. Their inner confidence and how they handle challenges
        5. Their values and what matters most to them
        
        Then create:
        1. A powerful, symbolic name for their Alter Ego (like Phoenix, Nova, Atlas, Orion, etc.)
           - If they're young, choose a name that suggests growth and potential
           - If they're creative, choose a name that reflects artistic energy
           - If they're analytical, choose a name that suggests wisdom and insight
           
        2. A compelling description of this Alter Ego that captures their essence
        
        Format your response as JSON:
        {{
            "name": "Alter Ego Name",
            "description": "A paragraph describing their Alter Ego and how it reflects their true self",
            "core_traits": ["trait1", "trait2", "trait3", "trait4", "trait5"],
            "values": ["value1", "value2", "value3"],
            "inner_strengths": "Description of their inner strengths and abilities",
            "guiding_principle": "A motto or principle that guides their Alter Ego"
        }}
        
        IMPORTANT: Make this deeply meaningful and personal to them based on your conversation.
        Use language that would resonate with their age and interests.
        """
        
        # Extract just the messages
        formatted_history = []
        for msg in conversation_history:
            formatted_history.append({"role": "user", "content": msg.get('user_message', '')})
            formatted_history.append({"role": "assistant", "content": msg.get('ai_response', '')})
        
        # Get alter ego data from Groq
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        messages = [
            {"role": "system", "content": analysis_prompt}
        ]
        messages.extend(formatted_history)
        
        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            raise Exception(f"Groq API error: {response.text}")
        
        response_data = response.json()
        ai_response = response_data["choices"][0]["message"]["content"]
        
        # Extract JSON from response
        import re
        json_match = re.search(r'({[\s\S]*})', ai_response)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = ai_response
            
        # Clean up the JSON string
        json_str = json_str.strip('`').replace('json\n', '').replace('\n', '')
        
        # Parse JSON
        alter_ego_data = json.loads(json_str)
        
        # Create alter ego in database
        create_alter_ego(
            user_id=user_id,
            name=alter_ego_data["name"],
            description=alter_ego_data["description"],
            traits=alter_ego_data["core_traits"],
            values=alter_ego_data["values"],
            communication_style=alter_ego_data.get("inner_strengths", ""),
            challenges=[], # No longer tracking challenges
            decision_making=alter_ego_data.get("guiding_principle", "")
        )
        
        return {
            "name": alter_ego_data["name"],
            "description": alter_ego_data["description"]
        }
        
    except Exception as e:
        print(f"Error creating alter ego: {str(e)}")
        # Fallback alter ego - more personalized default
        return {
            "name": "Nova",
            "description": f"The bright inner light within {user_name} that combines creativity, resilience, and untapped potential. Nova represents your capacity to shine brilliantly even through challenges, illuminating new paths forward with wisdom and courage."
        }
    
# ------------------ Dashboard Routes ------------------
@dashboard_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    #return render_template('dashboard/index.html')
    return render_template('smart_diary/index.html')

# ------------------ Mood Canvas Routes ------------------
@mood_canvas_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    return render_template('smart_diary/index.html')

# ------------------ Profile Routes ------------------
@profile_bp.route('/')
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    return render_template('profile/index.html')


# ----------------- Smart Diary Routes -----------------

smart_diary_bp = Blueprint('smart_diary', __name__)

@smart_diary_bp.route('/')
def index():
    """Render the smart diary page"""
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    user_id = session['user_id']
    
    # Get alter ego for personalization
    alter_ego = get_alter_ego(user_id)
    
    # Get diary dates for initial load
    dates = get_all_diary_dates_with_preview(user_id)
    
    return render_template('smart_diary/index.html', 
                          entries=dates, 
                          alter_ego=alter_ego)

@smart_diary_bp.route('/entries')
def get_entries():
    """Get all diary entries grouped by date"""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session['user_id']
    
    # Get all diary dates with preview information
    dates_with_preview = get_all_diary_dates_with_preview(user_id)
    
    # Format for frontend
    formatted_entries = []
    for date_data in dates_with_preview:
        formatted_entries.append({
            "id": date_data["id"],  # Date string as ID
            "title": date_data["title"],
            "created_at": date_data["id"] + "T00:00:00",  # ISO format
            "has_ai_response": date_data["has_ai_responses"],
            "content": date_data["preview"],
            "liked": False  # Default value, could be stored in database later
        })
    
    return jsonify({"entries": formatted_entries})

@smart_diary_bp.route('/entry', methods=['POST'])
def create_entry():
    """Create a new diary entry from notepad content"""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session['user_id']
    data = request.json
    
    user_msg = data.get('content', '')
    title = data.get('title', 'Untitled')
    
    if not user_msg:
        return jsonify({"success": False, "error": "Empty content"}), 400
    
    # Get today's date
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Add new entry
    entry_id = add_diary_entry(user_id, today, user_msg)
    
    # Update title if provided
    if title != 'Untitled':
        update_date_title(user_id, today, title)
    
    # Generate alter ego response
    alter_ego = get_alter_ego(user_id)
    alter_ego_response = None
    
    if alter_ego:
        try:
            # Generate response from alter ego
            alter_ego_response = generate_alter_ego_response(user_msg, alter_ego)
            
            # Update entry with response
            update_entry_with_response(user_id, today, entry_id, alter_ego_response)
            
            # Also store in vector database
            from app.utils.vector_utils import store_diary_entry_vector
            store_diary_entry_vector(user_id, user_msg, today, entry_id, alter_ego_response)
            
        except Exception as e:
            print(f"Error generating alter ego response: {str(e)}")
    
    return jsonify({
        "success": True, 
        "entry_id": entry_id,
        "date": today,
        "response": alter_ego_response
    })


@smart_diary_bp.route('/entry/<date_str>')
def get_entries_for_date_route(date_str):
    """Get all entries for a specific date"""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session['user_id']
    
    try:
        # Validate date format
        datetime.strptime(date_str, '%Y-%m-%d')
        
        # Log what we're doing to help debug
        print(f"Fetching entries for user {user_id} and date {date_str}")
        
        # Get entries for this date
        date_data = get_entries_for_date(user_id, date_str)
        
        #print(f"Retrieved date data: {date_data}")
        
        if not date_data or not date_data.get("entries"):
            return jsonify({"entry": None})
        
        entries = date_data.get("entries", [])
        title = date_data.get("title", "Untitled")
        
        # Format entry for display
        formatted_entry = {
            "id": date_str,
            "title": title,
            "content": entries[0].get("user_msg", "") if entries else "",
            "created_at": date_str + "T00:00:00",  # ISO format
            "mood": "neutral",  # Default value
            "messages": []
        }
        
        # Add conversation pairs as messages
        for entry in entries:
            # Add user message
            formatted_entry["messages"].append({
                "sender": "user",
                "content": entry.get("user_msg", ""),
                "timestamp": entry.get("timestamp").isoformat() if entry.get("timestamp") else datetime.now().isoformat()
            })
            
            # Add alter ego response if it exists
            if entry.get("alter_ego_msg"):
                formatted_entry["messages"].append({
                    "sender": "alter_ego",
                    "content": entry.get("alter_ego_msg", ""),
                    "timestamp": entry.get("timestamp").isoformat() if entry.get("timestamp") else datetime.now().isoformat()
                })
        
        return jsonify({"entry": formatted_entry})
        
    except ValueError:
        return jsonify({"error": "Invalid date format"}), 400
    except Exception as e:
        print(f"Error getting entries: {str(e)}")
        return jsonify({"error": "Failed to get entries"}), 500

@smart_diary_bp.route('/entry/<date_str>', methods=['DELETE'])
def delete_entry(date_str):
    """Delete all entries for a specific date"""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session['user_id']
    
    try:
        success = delete_date_entries(user_id, date_str)
        return jsonify({"success": success})
    except Exception as e:
        print(f"Error deleting entries: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@smart_diary_bp.route('/entry/<date_str>/title', methods=['PUT'])
def update_title(date_str):
    """Update the title for a specific date"""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session['user_id']
    data = request.json
    title = data.get('title', 'Untitled')
    
    try:
        success = update_date_title(user_id, date_str, title)
        return jsonify({"success": success})
    except Exception as e:
        print(f"Error updating title: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@smart_diary_bp.route('/entry/<date_str>/message', methods=['POST'])
def add_message_to_date(date_str):
    """Add a new message to an existing date's conversation"""
    if 'user_id' not in session:
        return jsonify({"error": "Not authenticated"}), 401
    
    user_id = session['user_id']
    data = request.json
    
    user_msg = data.get('content', '')
    
    if not user_msg:
        return jsonify({"success": False, "error": "Empty content"}), 400
    
    try:
        # Add new entry for this date
        entry_id = add_diary_entry(user_id, date_str, user_msg)
        
        # Generate alter ego response
        alter_ego = get_alter_ego(user_id)
        alter_ego_response = None
        
        if alter_ego:
            try:
                # Get previous entries for context
                date_data = get_entries_for_date(user_id, date_str)
                
                # Generate response from alter ego with context
                alter_ego_response = generate_alter_ego_response(
                    user_msg, 
                    alter_ego,
                    [entry.get("user_msg", "") for entry in date_data.get("entries", [])]
                )
                
                # Update entry with response
                update_entry_with_response(user_id, date_str, entry_id, alter_ego_response)
            except Exception as e:
                print(f"Error generating alter ego response: {str(e)}")
        
        return jsonify({
            "success": True, 
            "entry_id": entry_id,
            "response": alter_ego_response
        })
        
    except Exception as e:
        print(f"Error adding message: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

def generate_alter_ego_response(user_message, alter_ego, previous_messages=None):
    """Generate a deeply personalized alter ego response using vector similarity"""
    try:
        # Initialize Groq client
        client = groq.Groq(api_key=GROQ_API_KEY)
        
        # Get user ID from the session
        user_id = session.get('user_id')
        
        # Step 1: Find similar past entries using vector search
        from app.utils.vector_utils import find_similar_entries, extract_user_persona
        
        similar_entries = []
        user_persona = None
        
        if user_id:
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
        - Keep responses authentic, warm and conversational (100-150 words)
        - Be the companion who's genuinely excited to be part of their journey every step of the way
        """
        
        # Build conversation history
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add previous messages for context if available
        if previous_messages:
            for i, msg in enumerate(previous_messages[-2:]):  # Limit to last 2 for focus
                messages.append({"role": "user", "content": msg})
                # Only include responses for messages before the last one
                if i < len(previous_messages) - 1:
                    messages.append({
                        "role": "assistant", 
                        "content": f"[Your supportive inner voice responded]"
                    })
        
        # Add current message
        messages.append({"role": "user", "content": user_message})
        
        # Generate response
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=300
        )
        
        alter_ego_response = response.choices[0].message.content
        
        # Store this entry with vector embedding for future reference
        if user_id:
            from app.utils.vector_utils import store_diary_entry_vector
            # We'll store this asynchronously to not block the response
            import threading
            threading.Thread(
                target=store_diary_entry_vector,
                args=(user_id, user_message, datetime.now().strftime('%Y-%m-%d'), str(uuid.uuid4()), alter_ego_response)
            ).start()
        
        return alter_ego_response
        
    except Exception as e:
        print(f"Error generating response: {str(e)}")
        return "I'm here for you and believe in you. Whatever you're facing, we'll get through it together. Tell me more about what's on your mind."