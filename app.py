import streamlit as st
from src.vibe_shopping_agent import VibeShoppingAgent

# Page configuration
st.set_page_config(
    page_title="Vibe Shopping Assistant",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    """Initialize session state variables"""
    if "agent" not in st.session_state:
        st.session_state.agent = VibeShoppingAgent()

    # Initialize loading state
    if "is_loading" not in st.session_state:
        st.session_state.is_loading = False

    # Header
    st.title("🛍️ Vibe Shopping Assistant")
    st.markdown("*Your personal AI stylist that understands your vibe*")

    # Sidebar with examples and info
    with st.sidebar:
        if st.button("🔄 Start New Conversation", use_container_width=True):
            st.session_state.agent.reset_conversation()
            st.session_state.is_loading = False
            st.rerun()

        # Display current inferred attributes
        if st.session_state.agent.attributes:
            st.header("🎯 Inferred Style Attributes")
            for attr, value in st.session_state.agent.attributes.items():
                if isinstance(value, list):
                    st.write(
                        f"**{attr.replace('_', ' ').title()}:** {', '.join(map(str, value))}"
                    )
                else:
                    st.write(f"**{attr.replace('_', ' ').title()}:** {value}")

        st.divider()

        st.header("✨ How it works")
        st.markdown(
            """
        1. **Tell me your vibe** - Use natural language like "something cute for brunch"
        2. **Answer 1-2 follow-ups** - I'll ask targeted questions to understand your style
        3. **Get personalized recs** - Receive curated suggestions with styling explanations
        """
        )

        st.header("💡 Example queries")
        example_queries = [
            "something cute for brunch",
            "elegant date night outfit",
            "office ready look",
            "flowy summer vacation dress",
            "something bold for a party",
            "comfy weekend casual",
            "breathable summer top",
        ]

        for query in example_queries:
            if st.button(
                f"💬 {query}", key=f"example_{query}", use_container_width=True
            ):
                st.session_state.user_input = query
                st.rerun()

    if st.session_state.agent.conversation:
        st.header("💬 Conversation")

        for message in st.session_state.agent.conversation:
            with st.chat_message(message["role"]):
                st.write(message["content"])

    else:
        st.header("👋 Welcome!")
        st.markdown(
            """
        I'm your personal styling assistant! Tell me what vibe you're going for, and I'll help you find the perfect pieces.
        
        **Try saying something like:**
        - "I need something cute for brunch with friends"
        - "Looking for an elegant date night outfit"
        - "Want something comfortable but stylish for work"
        """
        )

    # Chat input - disabled when loading
    user_input = st.chat_input(
        (
            "Describe the vibe you're going for..."
            if not st.session_state.is_loading
            else "Processing your request..."
        ),
        key="user_input",
        disabled=st.session_state.is_loading,
    )

    # Handle example query from sidebar
    if "user_input" in st.session_state and st.session_state.user_input:
        user_input = st.session_state.user_input
        del st.session_state.user_input

    if user_input:
        # Immediately display the user's message
        with st.chat_message("user"):
            st.write(user_input)

        # Show loading indicator while processing
        with st.chat_message("assistant"):
            with st.spinner("Thinking about your perfect style..."):
                try:
                    st.session_state.is_loading = True
                    st.session_state.agent.process_query(user_input)
                except Exception as e:
                    st.error(f"Sorry, I encountered an error: {str(e)}")
                    st.info("Please try again with a different query.")
                finally:
                    st.session_state.is_loading = False

        # Rerun to update the display
        st.rerun()


def start_streamlit():
    """Entry point for poetry start command"""
    import subprocess
    import sys

    subprocess.run([sys.executable, "-m", "streamlit", "run", "app.py"])


if __name__ == "__main__":
    main()
