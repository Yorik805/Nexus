#!/usr/bin/env python3
"""Interactive semantic search demo using vector store."""

from __future__ import annotations

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)

# Add repo root to path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

logger.info("Importing memory modules...")
from plugins.memory.actions.write import write
from plugins.memory.actions.search import search
from plugins.memory import database
from plugins.memory.vector_store import reset_store
logger.info("Import complete")


# Sample sentences for semantic search
SENTENCES = [
    "The quick brown fox jumps over the lazy dog",
    "I love eating pizza on Friday nights",
    "Machine learning is transforming technology",
    "The weather today is sunny and warm",
    "Python is a powerful programming language",
    "Dogs are loyal and friendly companions",
    "Coffee helps me stay focused in the morning",
    "Cats prefer to nap in quiet places",
    "The mountains are beautiful in autumn",
    "I enjoy reading books before sleep",
    "Technology is advancing at a rapid pace",
    "Cooking healthy meals takes time and effort",
    "The ocean waves are calming to watch",
    "Music has the power to heal emotions",
    "Learning new skills boosts confidence",
    "The sunset painted the sky in orange and pink",
    "Running keeps my body and mind healthy",
    "Garden flowers bloom in springtime",
    "Artificial intelligence is revolutionizing industries",
    "Friendship is built on trust and respect",
    "The rain nourishes the plants and trees",
    "Writing helps organize my thoughts clearly",
    "Video games provide entertainment and challenge",
    "Nature is a source of inspiration and peace",
    "The stars shine brightly at night",
    "Travelling broadens your perspective on life",
    "Coding requires patience and logical thinking",
    "Meditation improves mental health and focus",
    "The forest is home to many wildlife species",
    "Dancing is a fun way to exercise",
    "Books transport you to different worlds",
    "The park is crowded on sunny weekends",
    "Learning languages opens cultural doors",
    "Photography captures moments in time",
    "The river flows gently through the valley",
    "Teamwork makes the dream work",
    "Gardening connects you with nature",
    "The moon illuminates the night sky",
    "Communication is key to relationships",
    "Adventure awaits those who seek it",
    "Sleep is essential for health and recovery",
    "Art expresses emotions beyond words",
    "The beach is perfect for relaxation",
    "Innovation drives progress forward",
    "Family bonds strengthen over shared meals",
    "The sun rises and sets each day",
    "Exercise improves physical and mental wellbeing",
    "Stories connect people across generations",
    "The wind carries seeds to new places",
    "Curiosity leads to discovery and growth",
]


def setup_demo() -> None:
    """Initialize the demo with sample sentences."""
    logger.info("Starting setup_demo...")
    print("Initializing vector store with 50 sample sentences...")
    logger.info("Calling reset_store()")
    reset_store()
    
    # Clean up database if it exists
    db_path = database.DATABASE_PATH
    logger.info(f"Database path: {db_path}")
    if db_path.exists():
        logger.info("Removing existing database")
        db_path.unlink()
    
    logger.info(f"Writing {len(SENTENCES)} sentences...")
    for i, sentence in enumerate(SENTENCES, 1):
        logger.debug(f"Writing sentence {i}: {sentence[:50]}...")
        resp = write({
            "title": f"Sentence {i}",
            "category": "IDEA",
            "content": sentence,
            "tags": ["demo", "sample"],
        })
        logger.debug(f"  Response: {resp['status']}")
        if resp['status'] != 'SUCCESS':
            logger.error(f"  Failed to write sentence {i}: {resp}")
        if i % 10 == 0:
            print(f"  → Stored {i}/{len(SENTENCES)} sentences")
            logger.info(f"Progress: {i}/{len(SENTENCES)} stored")
    
    logger.info(f"Setup complete! All {len(SENTENCES)} sentences stored and indexed")
    print(f"✓ All {len(SENTENCES)} sentences stored and indexed!\n")


def interactive_search() -> None:
    """Start interactive search loop."""
    logger.info("Starting interactive search loop")
    print("=" * 70)
    print("SEMANTIC SEARCH DEMO - Vector-based similarity search")
    print("=" * 70)
    print("Type a word or sentence to find related content.")
    print("Type 'quit' or 'exit' to stop.\n")
    
    while True:
        try:
            query = input("🔍 Enter search query: ").strip()
            logger.info(f"User entered query: '{query}'")
            
            if not query:
                logger.debug("Empty query, skipping")
                print("  (empty query)\n")
                continue
            
            if query.lower() in {"quit", "exit", "q"}:
                logger.info("User requested exit")
                print("Goodbye! 👋")
                break
            
            logger.info(f"Executing VECTOR search for: '{query}'")
            print(f"\nSearching for: '{query}'...")
            
            logger.debug("Calling search() with VECTOR type")
            resp = search({"type": "VECTOR", "query": query, "limit": 5})
            logger.info(f"Search response status: {resp['status']}")
            logger.debug(f"Full response: {resp}")
            
            if resp["status"] != "SUCCESS":
                logger.error(f"Search failed: {resp['message']}")
                print(f"  ❌ Error: {resp['message']}\n")
                continue
            
            results = resp["data"]["results"]
            logger.info(f"Got {len(results)} results")
            
            if not results:
                logger.info("No results found for query")
                print("  No related sentences found.\n")
                continue
            
            print(f"  Found {len(results)} related sentences:\n")
            for i, result in enumerate(results, 1):
                title = result.get("title", "Unknown")
                memory_id = result.get("memory_id", "")
                logger.debug(f"Result {i}: {title} ({memory_id})")
                print(f"    {i}. {title}")
                print(f"       └─ (ID: {memory_id[:8] if memory_id else 'N/A'}...)\n")
        
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
            print("\n\nInterrupted. Goodbye! 👋")
            break
        except Exception as exc:
            logger.exception(f"Exception during search: {exc}")
            print(f"  ❌ Error: {exc}\n")


def main() -> None:
    """Main entry point."""
    logger.info("=" * 70)
    logger.info("SEMANTIC SEARCH DEMO STARTING")
    logger.info("=" * 70)
    try:
        setup_demo()
        interactive_search()
    except Exception as exc:
        logger.exception(f"Fatal error in main: {exc}")
        raise
    finally:
        logger.info("Demo ended")


if __name__ == "__main__":
    main()
