"""
MCP Ebook Server - Provides AI-accessible tools for browsing and reading ebooks.

This server exposes MCP tools that allow AI assistants to:
- List all books in the library
- Get book metadata and chapter lists
- Read specific chapters or ranges
- Search within books or across the library
"""

import os
import json
import logging
from mcp.server.fastmcp import FastMCP
from .library import EbookLibrary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Get configuration from environment
LIBRARY_PATH = os.environ.get('EBOOK_LIBRARY_PATH', '/ebooks')
MCP_HOST = os.environ.get('MCP_HOST', '0.0.0.0')
MCP_PORT = int(os.environ.get('MCP_PORT', '8080'))

# Initialize the library
library = EbookLibrary(LIBRARY_PATH)

# Initialize FastMCP server with host/port for SSE transport
mcp = FastMCP(
    "ebook-server",
    host=MCP_HOST,
    port=MCP_PORT,
    instructions="""
    This is an ebook library server that provides access to a collection of books.
    Use these tools to browse, read, and search ebooks.

    Common workflows:
    1. Use list_books() to see what's available
    2. Use get_book_info() to see a book's contents as the printed book names them
    3. Use get_book_chapter() to read a chapter by its printed number or name
       ("8", "Chapter Eight", "Prologue"). get_chapter() takes a section index,
       which is the EPUB's file order and often differs from the printed chapter.
    4. Use search_book() to find specific content
    5. Use find_quote() to check a quotation and get the book's exact wording

    Book paths can be specified as:
    - Relative paths from the library root (e.g., "Author Name/Book Title.epub")
    - Full file paths
    - Just the filename (will search for matches)
    """
)


@mcp.tool()
def list_books() -> str:
    """
    List all ebooks in the library with their metadata.

    Returns a JSON array of book objects with:
    - title: Book title
    - author: Book author
    - relative_path: Path relative to library root (use this for other tools)
    - language: Book language (if available)
    """
    books = library.discover_books()
    # Simplify output for readability
    simplified = []
    for book in books:
        simplified.append({
            'title': book.get('title'),
            'author': book.get('author'),
            'relative_path': book.get('relative_path'),
            'language': book.get('language'),
        })
    return json.dumps(simplified, indent=2)


@mcp.tool()
def get_book_info(book_path: str) -> str:
    """
    Get detailed information about a specific book including its chapters.

    Args:
        book_path: Path to the book (relative to library or full path)

    Returns:
        JSON object with book metadata and chapter list, or error message
    """
    info = library.get_book_info(book_path)
    if info:
        return json.dumps(info, indent=2)
    return json.dumps({'error': f'Book not found: {book_path}'})


@mcp.tool()
def get_book_chapter(book_path: str, chapter: str) -> str:
    """
    Get a chapter the way a reader names it: the number or title printed in
    the book, such as "8", "eight", "Chapter VIII", "Prologue" or "Relaxation".
    Use this whenever someone refers to a chapter by number.

    Args:
        book_path: Path to the book (relative to library or full path)
        chapter: Printed chapter number or name

    Returns:
        JSON object with the printed chapter number, label, section indexes and text
    """
    result = library.get_book_chapter(book_path, chapter)
    if result is None:
        return f"Book not found: '{book_path}'"
    return json.dumps(result, indent=2)


@mcp.tool()
def find_quote(book_path: str, quote: str) -> str:
    """
    Check that a quotation appears in a book and get the exact wording with
    its chapter. Case, punctuation and quote styles are ignored, and "..."
    in the quote skips ahead. A close but inexact match is returned with
    "exact": false and the book's real wording.

    Args:
        book_path: Path to the book (relative to library or full path)
        quote: The passage to look for

    Returns:
        JSON object with exact, text, chapter, label, section and surrounding text
    """
    result = library.find_quote(book_path, quote)
    if result:
        return json.dumps(result, indent=2)
    return json.dumps({'message': f"Quote not found in '{book_path}'"})


@mcp.tool()
def get_section(book_path: str, section: int) -> str:
    """
    Get one reading-order section (EPUB file order, 1-indexed) with its
    printed chapter label, for readers that page through a book.

    Args:
        book_path: Path to the book (relative to library or full path)
        section: Section index from get_book_info contents

    Returns:
        JSON object with title, section, section_count, chapter, label and text
    """
    result = library.get_section(book_path, section)
    if result:
        return json.dumps(result)
    return json.dumps({'message': f"Section {section} not found in '{book_path}'"})


@mcp.tool()
def get_chapter(book_path: str, chapter_number: int) -> str:
    """
    Get the full text of one section by its index in file order (1-indexed).
    This index is not the printed chapter number; use get_book_chapter for that.

    Args:
        book_path: Path to the book (relative to library or full path)
        chapter_number: Section index (1-indexed, file order)

    Returns:
        The chapter text content, or error message if not found
    """
    content = library.get_chapter(book_path, chapter_number)
    if content:
        return content
    return f"Chapter {chapter_number} not found in '{book_path}'"


@mcp.tool()
def get_chapters_range(book_path: str, start_chapter: int, end_chapter: int) -> str:
    """
    Get the text content for a range of chapters.

    Args:
        book_path: Path to the book (relative to library or full path)
        start_chapter: Starting chapter number (1-indexed, inclusive)
        end_chapter: Ending chapter number (1-indexed, inclusive)

    Returns:
        The combined chapter text content, or error message if not found
    """
    content = library.get_chapters_range(book_path, start_chapter, end_chapter)
    if content:
        return content
    return f"Chapters {start_chapter}-{end_chapter} not found in '{book_path}'"


@mcp.tool()
def search_book(book_path: str, query: str) -> str:
    """
    Search for text within a specific book.

    Args:
        book_path: Path to the book (relative to library or full path)
        query: Text to search for (case, punctuation and quote styles ignored)

    Returns:
        JSON array of matches with the printed chapter, label, section and context
    """
    results = library.search_book(book_path, query)
    if results:
        return json.dumps(results, indent=2)
    return json.dumps({'message': f"No matches found for '{query}' in '{book_path}'"})


@mcp.tool()
def search_library(query: str) -> str:
    """
    Search for text across all books in the library.

    Args:
        query: Text to search for (case, punctuation and quote styles ignored)

    Returns:
        JSON array of matches with book info, printed chapter, label, and context
    """
    results = library.search_library(query)
    if results:
        return json.dumps(results, indent=2)
    return json.dumps({'message': f"No matches found for '{query}' in library"})


# Health check endpoint for Kubernetes
@mcp.resource("health://status")
def health_status() -> str:
    """Health check resource for monitoring."""
    books = library.discover_books()
    return json.dumps({
        'status': 'healthy',
        'library_path': LIBRARY_PATH,
        'book_count': len(books),
    })


def main():
    """Run the MCP server."""
    logger.info(f"Starting MCP Ebook Server on {MCP_HOST}:{MCP_PORT}")
    logger.info(f"Library path: {LIBRARY_PATH}")

    # Discover books on startup
    books = library.discover_books()
    logger.info(f"Found {len(books)} books in library")

    # Run with streamable-http transport for remote access (Cursor, Zed, etc.)
    mcp.run(transport="streamable-http")


if __name__ == "__main__":
    main()
