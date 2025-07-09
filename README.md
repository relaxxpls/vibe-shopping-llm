# 🛍️ AI-Powered Fashion Recommendation System

### 🌟 Key Features
- **Natural Language Processing**: Understands complex style descriptions like "cute brunch outfit" or "elegant date night look"
- **Intelligent Follow-ups**: AI decides when to ask clarifying questions for better recommendations
- **Dynamic Attribute Extraction**: No more hardcoded vibe mappings - the LLM extracts attributes from any input
- **Personalized Conversations**: Maintains context and provides engaging, human-like interactions
- **Modern Architecture**: Built with LangChain and OpenAI's GPT-4

### 🎯 Example Conversation
```
👤 User: "I need something cute for brunch"

🤖 AI Stylist: "Great! I found some lovely options for 'cute for brunch'. 
To help me find the perfect pieces for you, are you drawn to any 
particular colors or prints - maybe something pastel, neutral, or 
with a fun pattern?"

👤 User: "I love pastels!"

🤖 AI Stylist: "Perfect! Here are my top picks for you:

1. **Pastel Dreams Midi Dress** ($75)
   This adorable piece perfectly captures your cute brunch vibe with its 
   soft pastel pink hue and relaxed fit that's both comfortable and 
   effortlessly stylish.

2. **Lavender Linen Wrap Top** ($45)
   The gentle lavender color and breezy linen fabric create the perfect 
   casual-chic look for a leisurely brunch with friends.

3. **Mint Floral Sundress** ($89)
   This sweet sundress combines your love for pastels with a charming 
   floral print, creating an ideal brunch outfit that's both cute and 
   comfortable."
```

### 🛠️ Using the Vibe Shopping Agent
```python
from src.vibe_shopping_agent import VibeShoppingAgent

# Initialize the agent (requires OpenAI API key)
agent = VibeShoppingAgent()

# Have a natural conversation
response = agent.process_query("I want something elegant for a date night")
print(response)

# Continue the conversation
response = agent.process_query("I prefer fitted styles")
print(response)

# Get conversation summary
summary = agent.get_conversation_summary()
print(summary)

# Reset for new conversation
agent.reset_conversation()
```

## 🚀 Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd assignments

# Install dependencies
poetry install
poetry shell

# Set up OpenAI API key for the vibe shopping agent
export OPENAI_API_KEY="your-api-key-here"
```
