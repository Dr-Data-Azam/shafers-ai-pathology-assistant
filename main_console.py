# File: main_console.py
"""
Console interface for Shafer's Oral Pathology RAG System
"""

import logging
import sys
import time
from datetime import datetime

from chat_history_manager import clear_chat_history, load_chat_history
from config import configure_logging, get_config
from exceptions import ConfigError, LLMError, RetrieverError
from llm_provider_manager import get_available_providers
from rag_system import ask_question, get_system_info

logger = logging.getLogger(__name__)


def print_system_status():
    """Print system status and available providers"""
    print("Shafer's Oral Pathology Q&A System")
    print("=" * 50)

    system_info = get_system_info()

    if not system_info["vector_db_exists"]:
        print("Vector database not found!")
        print("Please run: python vector_store_creator.py")
        return False

    available_providers = system_info["available_providers"]

    if not available_providers:
        print("No API keys found!")
        print("Please set OPENAI_API_KEY or GROQ_API_KEY in your .env file")
        return False

    print(f"Available providers: {', '.join(available_providers)}")
    print(
        f"Vector database: {'Ready' if system_info['vector_db_exists'] else 'Missing'}"
    )
    print(
        f"Retriever cache: {'Ready' if system_info['retriever_cached'] else 'Will be created'}"
    )

    return True


def select_provider(available_providers):
    """Select LLM provider"""
    if len(available_providers) == 1:
        provider = available_providers[0]
        print(f"Using {provider.upper()} (only available provider)")
        return provider

    print("\nAvailable providers:")
    for i, provider in enumerate(available_providers, 1):
        from llm_provider_manager import get_provider_info

        info = get_provider_info(provider)
        print(f"  {i}. {provider.upper()} - {info.get('description', 'N/A')}")
        print(
            f"     Speed: {info.get('speed', 'N/A')} | Quality: {info.get('quality', 'N/A')}"
        )

    while True:
        try:
            choice = input(
                f"\nChoose provider (1-{len(available_providers)}): "
            ).strip()
            idx = int(choice) - 1
            if 0 <= idx < len(available_providers):
                return available_providers[idx]
            print(f"Please enter a number between 1 and {len(available_providers)}")
        except ValueError:
            print("Please enter a valid number")


def show_chat_history():
    """Display recent chat history"""
    history = load_chat_history()
    if not history:
        print("No chat history found")
        return

    print(f"\nRecent Chat History ({len(history)} total interactions):")
    print("-" * 80)

    recent_history = history[-10:]  # Show last 10
    for i, interaction in enumerate(recent_history, 1):
        timestamp = datetime.fromisoformat(interaction["timestamp"]).strftime(
            "%Y-%m-%d %H:%M"
        )
        print(
            f"{i}. [{timestamp}] [{interaction['provider']}] ({interaction['performance']['total_time']}s)"
        )
        print(f"   Q: {interaction['question'][:70]}...")
        if len(interaction["question"]) > 70:
            print(
                "      "
                + interaction["question"][70:140]
                + ("..." if len(interaction["question"]) > 140 else "")
            )
        print()


def interactive_chat():
    """Main interactive chat function"""
    if not print_system_status():
        return

    available_providers = get_available_providers()

    print("\nCommands:")
    print("  - 'switch' to change provider")
    print("  - 'history' to view chat history")
    print("  - 'clear' to clear chat history")
    print("  - 'status' to view system status")
    print("  - 'quit' to exit")
    print("=" * 50)

    # Select initial provider
    provider = select_provider(available_providers)
    print(f"\nUsing {provider.upper()} provider")

    while True:
        query = input(f"\n[{provider.upper()}] Enter your question: ").strip()

        if query.lower() in ["quit", "exit", "q"]:
            print("Goodbye!")
            break

        if query.lower() == "switch":
            if len(available_providers) == 1:
                print("Only one provider available. Cannot switch.")
                continue

            provider = select_provider(available_providers)
            print(f"Switched to {provider.upper()}")
            continue

        if query.lower() == "history":
            show_chat_history()
            continue

        if query.lower() == "clear":
            confirm = (
                input("Are you sure you want to clear chat history? (y/N): ")
                .strip()
                .lower()
            )
            if confirm == "y":
                if clear_chat_history():
                    print("Chat history cleared")
                else:
                    print("Error clearing chat history")
            continue

        if query.lower() == "status":
            print_system_status()
            continue

        if not query:
            continue

        print("Processing...")
        try:
            answer, stats = ask_question(query, provider)

            print("\nAnswer:")
            print("-" * 60)
            print(answer)
            print("-" * 60)
            print(
                f"{stats['total_time']:.1f}s | {stats['pages_retrieved']} pages | {stats['provider']}"
            )

        except LLMError as e:
            logger.error("LLMError: %s", e)
            print(f"AI provider error: {e.message}. Try switching providers.")
        except RetrieverError as e:
            logger.error("RetrieverError: %s", e)
            print("Retriever error: could not search the textbook. Exiting.")
            break
        except ConfigError as e:
            logger.error("ConfigError: %s", e)
            print(f"Configuration error: {e.message}")
            break


def test_both_providers():
    """Test both providers with a sample question"""
    if not print_system_status():
        return

    available_providers = get_available_providers()
    query = "How cellulitis is described in shafers?"

    print(f"\nTesting with sample question: '{query}'")
    print("=" * 60)

    for provider in available_providers:
        print(f"\nTesting {provider.upper()}...")
        try:
            start = time.time()
            answer, stats = ask_question(query, provider, save_history=False)
            end = time.time()

            print(f"{provider.upper()} completed in {end - start:.2f}s")
            print(
                f"Retrieved {stats['documents_retrieved']} docs from {stats['pages_retrieved']} pages"
            )
            print(f"Answer preview: {answer[:200]}...")

        except LLMError as e:
            logger.error("LLMError testing %s: %s", provider, e)
            print(f"{provider.upper()} failed (LLM error): {e.message}")
        except RetrieverError as e:
            logger.error("RetrieverError testing %s: %s", provider, e)
            print(f"{provider.upper()} failed (retriever error): {e.message}")
        except ConfigError as e:
            logger.error("ConfigError testing %s: %s", provider, e)
            print(f"{provider.upper()} failed (config error): {e.message}")


if __name__ == "__main__":
    try:
        configure_logging(get_config())
    except ConfigError as e:
        print(f"Configuration error: {e.message}", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_both_providers()
    else:
        interactive_chat()
