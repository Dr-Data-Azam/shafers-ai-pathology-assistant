import logging
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from chat_history_manager import (
    clear_chat_history,
    get_history_stats,
    load_chat_history,
)
from config import configure_logging, get_config
from exceptions import ConfigError, LLMError, RetrieverError
from llm_provider_manager import get_available_providers, get_provider_info
from rag_system import ask_question, get_system_info

configure_logging(get_config())
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="Shafer's Oral Pathology Q&A",
    page_icon="🦷",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown(
    """
<style>
    .main-header {
        font-size: 3rem;
        color: #2E86AB;
        text-align: center;
        margin-bottom: 2rem;
    }
    .provider-card {
        padding: 1rem;
        border-radius: 10px;
        margin: 0.5rem;
        border: 2px solid transparent;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .provider-card.selected {
        border-color: #2E86AB;
        background-color: rgba(46, 134, 171, 0.1);
    }
    .provider-card:hover {
        border-color: #2E86AB;
        transform: translateY(-2px);
    }
    .answer-box {
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 1px solid #ccc;
        background-color: var(--background-color);
        color: var(--text-color);
    }
    .stats-container {
        background-color: rgba(46, 134, 171, 0.1);
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .chat-bubble {
        padding: 1rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 4px solid #2E86AB;
        background-color: rgba(46, 134, 171, 0.05);
    }
    /* Dark mode compatibility */
    @media (prefers-color-scheme: dark) {
        .answer-box {
            background-color: #262730;
            color: #ffffff;
            border-color: #444;
        }
        .provider-card {
            background-color: #262730;
            color: #ffffff;
        }
        .provider-card.selected {
            background-color: rgba(46, 134, 171, 0.2);
        }
    }
</style>
""",
    unsafe_allow_html=True,
)


def initialize_session_state():
    """Initialize session state variables"""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "current_provider" not in st.session_state:
        providers = get_available_providers()
        st.session_state.current_provider = providers[0] if providers else None
    if "system_initialized" not in st.session_state:
        st.session_state.system_initialized = False


def check_system_status():
    """Check if the system is properly set up"""
    system_info = get_system_info()

    if not system_info["vector_db_exists"]:
        st.error(
            "Vector database not found! Please run `python vector_store_creator.py` first."
        )
        return False

    if not system_info["available_providers"]:
        st.error(
            "No API keys found! Please set OPENAI_API_KEY or GROQ_API_KEY in your .env file."
        )
        return False

    return True


def render_sidebar():
    """Render the simplified sidebar"""
    with st.sidebar:
        st.title("Shafer's Q&A")

        st.divider()

        # Book attribution
        st.markdown("""
        **Source:** Shafer's Textbook of Oral Pathology (7th Edition)  
        **Authors:** Shafer, Hine, Levy  
        **Editors:** R Rajendran, B Sivapathasundharam  
        **Publisher:** Elsevier  
        
        *All answers are based exclusively on content from this textbook.*
        """)

        st.divider()

        # Chat history stats
        st.subheader("Statistics")
        history_stats = get_history_stats()

        st.metric("Total Chats", history_stats.get("total_interactions", 0))
        st.metric("Avg Response Time", f"{history_stats.get('avg_response_time', 0)}s")

        st.divider()

        # Clear history button
        if st.button("Clear Chat History", type="secondary"):
            if clear_chat_history():
                st.success("Chat history cleared!")
                st.rerun()
            else:
                st.error("Error clearing history")


def render_main_chat():
    """Render the main chat interface"""
    st.markdown(
        '<h1 class="main-header">Shafer\'s Oral Pathology Q&A</h1>',
        unsafe_allow_html=True,
    )

    # Check available providers
    available_providers = get_available_providers()

    if not available_providers:
        st.error("No AI models available. Please check your API keys in the .env file.")
        return

    # Question input and model selection in the same row
    st.subheader("Ask Your Question")

    col1, col2 = st.columns([3, 1])

    with col1:
        question = st.text_area(
            "Enter your question about oral pathology:",
            height=120,
            value=st.session_state.get("current_question", ""),
            key="question_input",
            placeholder="Type your question here...",
            label_visibility="collapsed",
        )

    with col2:
        st.markdown("**Choose AI Model:**")

        # Create provider options with descriptions
        provider_options = {}
        for provider in available_providers:
            info = get_provider_info(provider)
            provider_options[
                f"{provider.upper()} ({info.get('speed', 'N/A')} speed)"
            ] = provider

        selected_provider_display = st.selectbox(
            "Model:",
            options=list(provider_options.keys()),
            key="provider_dropdown",
            label_visibility="collapsed",
        )

        st.session_state.current_provider = provider_options[selected_provider_display]

        # Show model info
        provider_info = get_provider_info(st.session_state.current_provider)
        st.caption(f"Quality: {provider_info.get('quality', 'N/A')}")
        st.caption(f"Cost: {provider_info.get('cost', 'N/A')}")

    # Sample questions dropdown
    sample_questions = [
        "Select a sample question...",
        "What are tooth development anomalies?",
        "Explain the classification of oral tumors",
        "What are the clinical features of oral cancer?",
        "Describe the pathogenesis of dental caries",
        "What is the difference between hyperplasia and hypertrophy?",
        "What are the stages of tooth development?",
        "Explain the histopathology of oral leukoplakia",
        "What are the different types of oral ulcers?",
        "Describe the features of oral lichen planus",
    ]

    selected_sample = st.selectbox(
        "💡 Or choose from sample questions:",
        options=sample_questions,
        key="sample_dropdown",
    )

    # If a sample question is selected, update the text area
    if (
        selected_sample != "Select a sample question..."
        and selected_sample != st.session_state.get("current_question", "")
    ):
        st.session_state.current_question = selected_sample
        st.rerun()

    # Submit and clear buttons
    col1, col2 = st.columns([3, 1])

    with col1:
        submit_button = st.button(
            "🔍 Ask Question",
            type="primary",
            disabled=not question.strip() or not st.session_state.current_provider,
            use_container_width=True,
        )

    with col2:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state.current_question = ""
            st.rerun()

    # Process question
    if submit_button and question.strip():
        with st.spinner(
            f"🤔 Processing with {st.session_state.current_provider.upper()}..."
        ):
            try:
                answer, stats = ask_question(
                    question, st.session_state.current_provider
                )

                # Display answer with better dark mode support
                st.markdown("---")
                st.subheader("📖 Answer")
                st.markdown(
                    f"""
                <div class="answer-box">
                    {answer.replace('\n', '<br>')}
                </div>
                """,
                    unsafe_allow_html=True,
                )

                # Display stats in a clean container
                st.markdown(
                    f"""
                <div class="stats-container">
                    <strong>Performance:</strong> {stats['total_time']:.1f}s response time | 
                    {stats['pages_retrieved']} pages retrieved | 
                    {stats['documents_retrieved']} documents analyzed | 
                    Model: {stats['provider']}
                </div>
                """,
                    unsafe_allow_html=True,
                )

                # Book reference reminder
                st.info(
                    "📚 Answer based on Shafer's Textbook of Oral Pathology (7th Edition)"
                )

                # Add to session chat history
                st.session_state.chat_history.append(
                    {
                        "timestamp": datetime.now(),
                        "question": question,
                        "answer": answer,
                        "provider": stats["provider"],
                        "stats": stats,
                    }
                )

                # Clear the input
                st.session_state.current_question = ""

            except LLMError as e:
                logger.error("LLMError in render_main_chat: %s", e)
                st.error(
                    "The AI provider is unavailable — please try again or switch providers."
                )
            except RetrieverError as e:
                logger.error("RetrieverError in render_main_chat: %s", e)
                st.error(
                    "Could not retrieve context from the textbook — "
                    "the vector database may need rebuilding."
                )
            except ConfigError as e:
                logger.error("ConfigError in render_main_chat: %s", e)
                st.error("Configuration error — please check your .env file.")


def render_chat_history():
    """Render chat history section"""
    st.subheader("Current Session History")

    if not st.session_state.chat_history:
        st.info("No questions asked in this session yet.")
        return

    # Display recent chats from current session
    for i, chat in enumerate(
        reversed(st.session_state.chat_history[-5:])
    ):  # Show last 5
        with st.expander(
            f"{chat['timestamp'].strftime('%H:%M:%S')} - {chat['question'][:60]}..."
        ):
            st.markdown(f"**Question:** {chat['question']}")
            st.markdown(f"**Answer:** {chat['answer']}")

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Time", f"{chat['stats']['total_time']:.1f}s")
            with col2:
                st.metric("Pages", chat["stats"]["pages_retrieved"])
            with col3:
                st.metric("Model", chat["stats"]["provider"])


def render_persistent_history():
    """Render persistent chat history from file"""
    st.subheader("All Chat History")

    history = load_chat_history()

    if not history:
        st.info("No chat history found.")
        return

    # Create DataFrame for better display
    df_data = []
    for entry in history:
        df_data.append(
            {
                "Time": datetime.fromisoformat(entry["timestamp"]).strftime(
                    "%m-%d %H:%M"
                ),
                "Question": (
                    entry["question"][:70] + "..."
                    if len(entry["question"]) > 70
                    else entry["question"]
                ),
                "Model": entry["provider"],
                "Response Time": f"{entry['performance']['total_time']}s",
                "Pages": entry["pages_retrieved"],
            }
        )

    df = pd.DataFrame(df_data)

    # Display options
    col1, col2 = st.columns([3, 1])
    with col1:
        show_count = st.selectbox("Show entries:", [10, 25, 50], index=0)
    with col2:
        if st.button("Show Analytics"):
            st.session_state.show_analytics = not st.session_state.get(
                "show_analytics", False
            )

    # Show recent entries
    st.dataframe(df.tail(show_count), use_container_width=True)

    # Analytics
    if st.session_state.get("show_analytics", False):
        st.subheader("Analytics")

        if len(history) > 1:
            # Response time chart
            response_times = [
                entry["performance"]["total_time"] for entry in history[-20:]
            ]
            timestamps = [
                datetime.fromisoformat(entry["timestamp"]).strftime("%H:%M")
                for entry in history[-20:]
            ]

            fig = go.Figure()
            fig.add_trace(
                go.Scatter(
                    x=timestamps,
                    y=response_times,
                    mode="lines+markers",
                    name="Response Time",
                    line=dict(color="#2E86AB"),
                )
            )
            fig.update_layout(
                title="Response Time Trend (Last 20 queries)",
                xaxis_title="Time",
                yaxis_title="Response Time (seconds)",
                height=400,
            )
            st.plotly_chart(fig, use_container_width=True)

            # Provider usage
            provider_counts = {}
            for entry in history:
                provider = entry["provider"]
                provider_counts[provider] = provider_counts.get(provider, 0) + 1

            if provider_counts:
                fig_pie = px.pie(
                    values=list(provider_counts.values()),
                    names=list(provider_counts.keys()),
                    title="Model Usage Distribution",
                )
                st.plotly_chart(fig_pie, use_container_width=True)


def main():
    """Main application function"""
    initialize_session_state()

    # Check system status
    if not check_system_status():
        st.stop()

    st.session_state.system_initialized = True

    # Render sidebar
    render_sidebar()

    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["Chat", "Session History", "All History"])

    with tab1:
        render_main_chat()

    with tab2:
        render_chat_history()

    with tab3:
        render_persistent_history()

    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666;'>"
        "Shafer's Oral Pathology Q&A System"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
