# app/llm/alter_ego_processor.py
import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up API key
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"  # Use appropriate Llama model available through Groq

def get_alter_ego_response(user_message, alter_ego, entry_content=None, previous_messages=None):
    """
    Generate a response from the user's alter ego using LLM
    
    Args:
        user_message: Current message from the user
        alter_ego: The alter ego data object
        entry_content: Optional context from the diary entry
        previous_messages: Optional list of previous messages
    
    Returns:
        Generated response text
    """
    try:
        if not alter_ego:
            # Fallback if no alter ego exists
            alter_ego_name = "Reflector"
            alter_ego_desc = "An insightful companion who helps you process your thoughts and feelings."
            traits = ["empathetic", "reflective", "supportive", "intuitive", "encouraging"]
            values = ["authenticity", "growth", "self-awareness"]
            communication_style = "Warm and thoughtful, asking meaningful questions"
        else:
            alter_ego_name = alter_ego.get("name", "Reflector")
            alter_ego_desc = alter_ego.get("description", "An insightful companion who helps you process your thoughts and feelings.")
            traits = alter_ego.get("traits", ["empathetic", "reflective", "supportive"])
            values = alter_ego.get("values", ["authenticity", "growth"])
            communication_style = alter_ego.get("communication_style", "Warm and thoughtful")
        
        # Build context from previous messages if available
        conversation_context = ""
        if previous_messages:
            for msg in previous_messages[-5:]:  # Use last 5 messages for context
                sender = "You" if msg.get("sender") == "alter_ego" else "User"
                conversation_context += f"{sender}: {msg.get('content', '')}\n"
        
        # Build prompt for the LLM
        system_prompt = f"""You are {alter_ego_name}, an alter ego character that responds to a user's diary entries.
        
About you:
- You are: {alter_ego_desc}
- Your traits: {', '.join(traits)}
- Your values: {', '.join(values)}
- Your communication style: {communication_style}

Your task is to respond to the user's diary entry with empathy, insight, and authenticity.
You should respond as if you are the user's alter ego - a part of them that can provide reflection and perspective.

Guidelines:
1. Keep responses conversational, warm, and personal
2. Ask thoughtful questions that encourage self-reflection
3. Recognize emotions in the user's writing and acknowledge them
4. Offer gentle insights about patterns or themes you notice
5. Be supportive and encouraging, never judgmental
6. Keep responses relatively brief (3-5 sentences)
7. Speak in the first person as if you are an extension of the user, not a separate entity
8. Do not identify yourself as AI, LLM, or assistant - you are their alter ego

IMPORTANT: You are NOT a therapist or counselor, but a reflective part of the user's own mind.
For serious mental health concerns, gently suggest seeking professional help rather than attempting to solve their problem.
"""

        # Create request payload
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add entry content as context if available
        if entry_content:
            messages.append({"role": "system", "content": f"The user's diary entry: {entry_content}"})
        
        # Add conversation context if available
        if conversation_context:
            messages.append({"role": "system", "content": f"Previous conversation:\n{conversation_context}"})
        
        # Add the user's current message
        messages.append({"role": "user", "content": user_message})
        
        # Configure API request
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 400  # Keep responses reasonably short
        }
        
        # Make API request
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            print(f"LLM API error: {response.text}")
            return get_fallback_response(user_message)
        
        response_data = response.json()
        return response_data["choices"][0]["message"]["content"]
    
    except Exception as e:
        print(f"Error generating alter ego response: {str(e)}")
        return get_fallback_response(user_message)

def get_fallback_response(user_message):
    """Generate a fallback response when the LLM is unavailable"""
    # Simple rule-based responses as fallback
    if "?" in user_message:
        return "That's an interesting question. What do you think? I find that we often know more than we realize when we take time to reflect."
    
    if any(word in user_message.lower() for word in ["sad", "upset", "depressed", "unhappy"]):
        return "I notice you're expressing some difficult emotions. Remember to be gentle with yourself. What small thing might bring you comfort right now?"
    
    if any(word in user_message.lower() for word in ["happy", "excited", "joy", "good"]):
        return "I can feel your positive energy! These moments are worth savoring. What specifically made this experience meaningful for you?"
    
    # Default fallback
    return "I appreciate you sharing that. What feelings come up for you as you reflect on this? Sometimes writing things down helps us understand ourselves better."