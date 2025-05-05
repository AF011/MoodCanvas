# MoodCanvas

> **Your only war is to defeat your yesterday's self**

MoodCanvas is a personalized personality development application that creates a unique "alter ego" companion to guide you on your journey of self-improvement and emotional growth.

## 🌟 Core Vision

MoodCanvas transforms the way we approach personal development by creating an AI-powered alter ego that truly understands you. Through initial conversations, mood tracking, and daily journaling, your alter ego evolves alongside you, providing personalized guidance, motivation, and a supportive presence accessible both through the app and WhatsApp.

## ✨ Key Features

### Personalized Alter Ego Creation
- Interactive initial session that deeply understands your personality traits, values, and communication style
- Creation of a unique "alter ego" companion tailored specifically to your personal profile
- Your alter ego evolves over time as it learns more about you through your interactions

### Smart Diary
- Write daily entries that help your alter ego understand your thoughts and emotions
- Receive personalized responses that provide insight, guidance, and emotional support
- Your diary becomes a conversation with your most understanding self

### WhatsApp Integration
- Connect with your alter ego anytime through WhatsApp
- Seamless synchronization between app entries and WhatsApp conversations
- All interactions contribute to your alter ego's understanding of you
- Simple command system for accessing features remotely

### Evolving Relationship
- The more you interact, the better your alter ego understands you
- Your alter ego adapts its communication style to match your preferences
- Build a consistent relationship with a companion who knows your history

## 🚀 Technology Stack

- **Backend**: Flask (Python), MongoDB
- **AI Integration**: LLaMA-4 (via Groq API)
- **Messaging**: Twilio WhatsApp API
- **Natural Language Processing**: Sentence Transformers for vector embeddings
- **Authentication**: JWT-based system

## 📋 Project Structure

```
MoodCanvas/
├── app/
│   ├── __init__.py             # App initialization
│   ├── routes/
│   │   ├── __init__.py         # Route definitions
│   │   └── reminder_routes.py  # Reminder API endpoints
│   ├── utils/
│   │   ├── db_utils.py         # Database utility functions
│   │   ├── vector_utils.py     # Vector embedding utilities
│   │   ├── whatsapp_utils.py   # WhatsApp integration tools
│   │   └── reminder_utils.py   # Reminder system functions
│   ├── whatsapp_integration.py # WhatsApp webhook handler
│   └── templates/              # HTML templates
├── run.py                      # Application entry point
└── requirements.txt            # Project dependencies
```

## 🛠️ Installation and Setup

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/MoodCanvas.git
   cd MoodCanvas
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set up environment variables in `.env` file:
   ```
   MONGO_URI=mongodb://localhost:27017/
   DB_NAME=MoodCanvas
   SECRET_KEY=your_secret_key
   GROQ_API_KEY=your_groq_api_key
   TWILIO_ACCOUNT_SID=your_twilio_account_sid
   TWILIO_AUTH_TOKEN=your_twilio_auth_token
   TWILIO_WHATSAPP_NUMBER=your_twilio_whatsapp_number
   ```

4. Start MongoDB:
   ```
   mongod
   ```

5. Run the application:
   ```
   python run.py
   ```

## 📱 WhatsApp Integration Guide

1. Set up a Twilio account and access the WhatsApp Sandbox
2. Configure the webhook URL to point to your server: `https://your-domain.com/whatsapp/webhook`
3. Users can connect by:
   - Adding the Twilio WhatsApp number to contacts
   - Sending the sandbox join code
   - Registering with `/register their-email@example.com`
4. Available commands:
   - `/help` - Show all commands
   - `/status` - Check connection status
   - `/reminders` - List active reminders
   - `/reminder daily 08:00 Morning check-in` - Create a reminder
   - `/unregister` - Unlink WhatsApp

## 🔮 Future Development

- **Task Management System**: Allow your alter ego to remember tasks, set deadlines, and provide gentle reminders
- **Gamified User Profile**: Visual representation of your growth journey with daily signature images
- **Mood Analytics**: Statistical insights into emotional patterns with personalized recommendations
- **Media Recommendations**: Curated book, music, and activity suggestions based on your current emotional state
- **Voice Interaction**: Communicate with your alter ego through voice messages and receive voice responses
- **Expanded Reminder System**: More sophisticated scheduling and personalized check-ins
- **Wearable Integration**: Passive mood tracking through connected devices

## 👥 Team

- Abdul Faheem (Leo Programmer - AF011)
- B. Kumara Kousik
- R. Shrinvass
- G. Kalyan Sagar

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

- Twilio for the WhatsApp Business API
- Groq for LLM API access
- MongoDB for document storage
- Flask community for the web framework