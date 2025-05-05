# app/utils/vector_utils.py
import numpy as np
from sentence_transformers import SentenceTransformer
import os
from dotenv import load_dotenv
from datetime import datetime
from bson.objectid import ObjectId
import json
import groq
from groq import Groq

# Load environment variables
load_dotenv()

# Set up Groq API key (already in your environment)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL = "meta-llama/llama-4-scout-17b-16e-instruct"

# MongoDB setup is imported from db_utils
from app.utils.db_utils import db

# Create a vector collection in MongoDB
vector_collection = db.vector_entries

# Load sentence transformer model (this runs locally)
# We'll use a lightweight model that still provides good embeddings
model = SentenceTransformer('all-MiniLM-L6-v2')

def get_embedding(text):
    """Get embedding vector for text using SentenceTransformers locally"""
    try:
        # Generate embedding (runs on CPU, no API needed)
        embedding = model.encode(text)
        
        # Convert to list for MongoDB storage
        return embedding.tolist()
    
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        return None

def store_diary_entry_vector(user_id, entry_text, date_str, entry_id, alter_ego_response=None):
    """Store diary entry with vector embedding"""
    embedding = get_embedding(entry_text)
    
    if embedding:
        vector_doc = {
            "user_id": ObjectId(user_id),
            "entry_id": entry_id,
            "date": date_str,
            "text": entry_text,
            "response": alter_ego_response,
            "embedding": embedding,
            "created_at": datetime.now()
        }
        
        vector_collection.insert_one(vector_doc)
        return True
    
    return False

def find_similar_entries(user_id, query_text, limit=5):
    """Find similar diary entries using vector similarity"""
    query_embedding = get_embedding(query_text)
    
    if not query_embedding:
        return []
    
    # Convert to numpy for vector calculations
    query_vector = np.array(query_embedding)
    
    # Get all entries for this user
    entries = list(vector_collection.find({"user_id": ObjectId(user_id)}))
    
    if not entries:
        return []
    
    # Calculate similarity scores
    results = []
    for entry in entries:
        entry_vector = np.array(entry["embedding"])
        # Calculate cosine similarity
        similarity = np.dot(query_vector, entry_vector) / (np.linalg.norm(query_vector) * np.linalg.norm(entry_vector))
        
        results.append({
            "entry_id": entry["entry_id"],
            "date": entry["date"],
            "text": entry["text"],
            "response": entry["response"],
            "similarity": float(similarity)
        })
    
    # Sort by similarity (highest first)
    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:limit]

def extract_user_persona(user_id):
    """Extract user persona from all vectorized entries using Groq instead of OpenAI"""
    entries = list(vector_collection.find({"user_id": ObjectId(user_id)}))
    
    if not entries or len(entries) < 3:  # Need at least 3 entries
        return None
    
    # Collect all user texts
    all_texts = [entry["text"] for entry in entries]
    combined_text = "\n\n".join(all_texts)
    
    # Use Groq to analyze the persona
    try:
        client = groq.Groq(api_key=GROQ_API_KEY)
        
        prompt = f"""Analyze the following diary entries from a user and extract their communication style, 
        personality traits, common phrases, speech patterns, and emotional tendencies.
        
        DIARY ENTRIES:
        {combined_text[:2000]}  # Only use first 2000 chars to avoid token limits
        
        Provide results in JSON format with these keys:
        - speech_patterns: Common phrases, sentence structures they use
        - communication_style: How they express themselves 
        - personality: Apparent personality traits
        - emotional_tendencies: How they tend to express emotions
        - interests: Topics they frequently mention
        """
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": "You analyze writing style to extract authentic user personas."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        analysis = response.choices[0].message.content
        
        # Extract JSON
        import re
        json_match = re.search(r'({[\s\S]*})', analysis)
        if json_match:
            json_str = json_match.group(1)
            analysis_json = json.loads(json_str)
            return analysis_json
        
        return None
    
    except Exception as e:
        print(f"Error analyzing user persona: {str(e)}")
        return None