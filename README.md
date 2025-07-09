# 🛍️ AI-Powered Fashion Recommendation System

A comprehensive AI-powered fashion recommendation system featuring both a sophisticated outfit recommendation engine and an intelligent vibe shopping agent that understands natural language style preferences.

## ✨ Features

### 🎯 Multiple Matching Strategies
- **Rule-Based Matching**: Exact and fuzzy attribute matching with weighted scoring
- **Embedding-Based Matching**: Semantic similarity using sentence transformers
- **LLM-Based Matching**: GPT-powered sophisticated reasoning (optional, requires API key)
- **Hybrid Matching**: Combines multiple strategies for optimal results

### 🔍 Smart Matching Capabilities
- **Flexible Input**: Accepts completion objects with various style attributes
- **Fuzzy Matching**: Handles synonyms and variations (e.g., "body hugging" matches "fitted")
- **Category Filtering**: Get recommendations for specific product categories
- **Weighted Scoring**: Prioritizes important attributes like fit and fabric
- **Detailed Explanations**: Provides reasoning for each recommendation

### 🎨 Style Understanding
- **Fit**: Relaxed, Body hugging, Tailored, Slim, etc.
- **Fabric**: Satin, Silk, Cotton, Linen, Chiffon, etc.
- **Color/Print**: Pastel colors, floral prints, bold colors, etc.
- **Occasion**: Party, Vacation, Office, Casual, etc.
- **Details**: Sleeve length, neckline, length, etc.

## 🤖 AI Vibe Shopping Agent (New!)

The modernized vibe shopping agent uses advanced LLM technology to understand natural language style requests and provide personalized recommendations.

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
pip install -r requirements.txt

# Set up OpenAI API key for the vibe shopping agent
export OPENAI_API_KEY="your-api-key-here"
```

### Basic Usage

#### Option 1: AI Vibe Shopping Agent (Recommended)
```python
from src.vibe_shopping_agent import VibeShoppingAgent

# Initialize the AI agent
agent = VibeShoppingAgent()

# Start a natural conversation
response = agent.process_query("I want something cute for brunch")
print(response)

# Continue the conversation
response = agent.process_query("I prefer pastels")
print(response)
```

#### Interactive Vibe Shopping Agent
```bash
# Run the interactive chat interface
python src/vibe_shopping_agent.py
```

#### Option 2: Direct Outfit Recommendation Engine
```python
from src.find_recommendations import OutfitRecommendationAgent

# Initialize the recommendation engine
agent = OutfitRecommendationAgent()

# Define style requirements (completion object)
completion = {
    "fit": "Body hugging",
    "fabric": ["Satin", "Silk"],
    "color_or_print": "Sapphire blue"
}

# Get recommendations
recommendations = agent.find_recommendations(
    completion, 
    strategy='hybrid',  # or 'rule_based', 'embedding_based', 'llm_based'
    max_results=5
)

# Display results
for rec in recommendations:
    print(f"{rec.product_name} - Score: {rec.match_score:.3f}")
    print(f"Price: ${rec.product_details['price']}")
    print(f"Reasoning: {rec.reasoning}")
    print("-" * 50)
```

## 🎯 Matching Strategies

### 1. Rule-Based Matching
- **How it works**: Exact and fuzzy attribute matching with weighted scoring
- **Strengths**: Fast, interpretable, handles synonyms
- **Use case**: When you need exact attribute matches with clear reasoning

```python
# Example: Find body-hugging satin/silk pieces
completion = {
    "fit": "Body hugging",
    "fabric": ["Satin", "Silk"]
}

recommendations = agent.find_recommendations(completion, strategy='rule_based')
```

### 2. Embedding-Based Matching
- **How it works**: Semantic similarity using sentence transformers
- **Strengths**: Understands context and overall style coherence
- **Use case**: When you want semantic understanding beyond exact matches

```python
# Example: Find pieces with overall elegant evening vibe
completion = {
    "fit": "Tailored",
    "fabric": "Silk",
    "occasion": "Party"
}

recommendations = agent.find_recommendations(completion, strategy='embedding_based')
```

### 3. LLM-Based Matching (Optional)
- **How it works**: GPT-powered sophisticated reasoning
- **Strengths**: Human-like fashion understanding and complex reasoning
- **Requirements**: OpenAI API key
- **Use case**: For most sophisticated fashion expertise

```python
# Set environment variable: OPENAI_API_KEY=your_key_here
recommendations = agent.find_recommendations(completion, strategy='llm_based')
```

### 4. Hybrid Matching (Recommended)
- **How it works**: Combines rule-based and embedding-based strategies
- **Strengths**: Best of both worlds with agreement bonuses
- **Use case**: Default choice for most scenarios

```python
# Recommended approach
recommendations = agent.find_recommendations(completion, strategy='hybrid')
```

## 📊 Example Completion Objects

### Date Night Elegance
```python
{
    "fit": "Body hugging",
    "fabric": ["Satin", "Velvet", "Silk"],
    "occasion": "Party",
    "color_or_print": "Sapphire blue"
}
```

### Garden Party Dress
```python
{
    "fit": "Relaxed",
    "fabric": ["Chiffon", "Linen"],
    "sleeve_length": "Short flutter sleeves",
    "color_or_print": "Pastel floral",
    "occasion": "Party"
}
```

### Summer Vacation
```python
{
    "fit": "Relaxed",
    "fabric": "Linen",
    "sleeve_length": "Spaghetti straps",
    "color_or_print": "Seafoam green",
    "occasion": "Vacation"
}
```

### Office Ready
```python
{
    "fabric": "Cotton poplin",
    "neckline": "Collar",
    "fit": "Tailored"
}
```

## 🛠️ Advanced Features

### Category-Specific Recommendations
```python
# Get only dress recommendations
dress_recommendations = agent.get_category_recommendations(
    completion, 
    category='dress',
    strategy='hybrid',
    max_results=3
)
```

### Strategy Comparison
```python
# Compare results across different strategies
comparison = agent.compare_strategies(completion, max_results=5)

for strategy, results in comparison.items():
    print(f"\n{strategy.upper()} Strategy:")
    for result in results:
        print(f"  {result.product_name} (Score: {result.match_score:.3f})")
```

### Detailed Explanations
```python
# Get detailed explanation for a recommendation
explanation = agent.explain_recommendation(recommendations[0])
print(explanation)
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
# Run all tests
python tests/test_recommendations.py

# Run specific agent tests
python tests/test_agent.py

# Run the original demo
python tests/demo.py
```

## 📁 Project Structure

```
assignments/
├── src/
│   ├── find_recommendations.py     # Main recommendation engine
│   └── vibe_shopping_agent.py      # AI-powered vibe shopping agent (LLM-based)
├── tests/
│   ├── test_recommendations.py     # Comprehensive tests
│   ├── test_agent.py              # Original agent tests
│   └── demo.py                    # Demo script
├── data/
│   ├── Apparels_shared.xlsx       # Product catalog (70 items)
│   ├── training.json              # Training examples
│   └── vibe_to_attribute.txt      # Vibe mappings
├── app.py                         # Streamlit web interface
├── requirements.txt               # Dependencies
└── README.md                      # This file
```

## 🎯 Performance Results

Based on comprehensive testing:

### Rule-Based Matching
- **Speed**: ⚡ Very Fast
- **Accuracy**: 🎯 High for exact matches
- **Interpretability**: 📊 Excellent

### Embedding-Based Matching
- **Speed**: ⚡ Fast (after initial model loading)
- **Accuracy**: 🎯 High for semantic similarity
- **Interpretability**: 📊 Good

### Hybrid Matching
- **Speed**: ⚡ Fast
- **Accuracy**: 🎯 Excellent (combines strengths)
- **Interpretability**: 📊 Very Good

## 🔧 Configuration

### Customize Attribute Weights
```python
# Custom weights for rule-based matching
custom_weights = {
    'fit': 1.0,
    'fabric': 0.9,
    'color_or_print': 0.8,
    'occasion': 0.7,
    'sleeve_length': 0.6
}

custom_matcher = RuleBasedMatcher(weights=custom_weights)
```

### Use Different Embedding Models
```python
# Use different sentence transformer model
custom_embedding_matcher = EmbeddingBasedMatcher(
    model_name='all-mpnet-base-v2'  # More powerful but slower
)
```

## 📈 Example Results

### Test Case: Body Hugging Satin/Silk
```
Input: {"fit": "Body hugging", "fabric": ["Satin", "Silk"]}

Results:
1. Radiant Ripple Halter (Score: 1.900)
   - Matches: fit, fabric
   - Price: $90
   - Reasoning: Perfect fit and fabric match

2. Midnight Mosaic Midi (Score: 1.900)
   - Matches: fit, fabric
   - Price: $185
   - Reasoning: Elegant satin dress with fitted silhouette

3. Storm Skyline Slip (Score: 1.900)
   - Matches: fit, fabric
   - Price: $160
   - Reasoning: Sleek body-hugging satin slip
```

### Test Case: Summer Vacation Linen
```
Input: {"fit": "Relaxed", "fabric": "Linen", "occasion": "Vacation"}

Results:
1. Ripple Linen Mini (Score: 3.400)
   - Matches: fit, fabric, color, occasion
   - Price: $95
   - Reasoning: Perfect vacation piece with all attributes

2. Ocean Haze Wide-Leg (Score: 2.700)
   - Matches: fit, fabric, color
   - Price: $92
   - Reasoning: Comfortable linen in vacation-perfect color
```

## 🌟 Key Innovations

### 1. **Multi-Strategy Architecture**
- Pluggable matching strategies
- Easy to extend with new approaches
- Consistent API across all strategies

### 2. **Intelligent Fuzzy Matching**
- Comprehensive synonym mapping
- Context-aware attribute matching
- Handles fashion terminology variations

### 3. **Hybrid Scoring System**
- Weighted combination of strategies
- Agreement bonuses for multi-strategy consensus
- Balanced approach to recommendation quality

### 4. **Rich Result Objects**
- Detailed matching information
- Comprehensive product details
- Clear reasoning for each recommendation

## 🔮 Future Enhancements

- **Image Analysis**: Visual similarity matching
- **Trend Analysis**: Incorporate fashion trends
- **User Preferences**: Personalized recommendations
- **Ensemble Matching**: Complete outfit coordination
- **Price Optimization**: Budget-aware recommendations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add your enhancement
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is open source and available under the MIT License.

---

*Built with ❤️ for fashion enthusiasts and AI developers*
