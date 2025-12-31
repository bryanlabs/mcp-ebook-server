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

# Initialize FastMCP server with host/port in constructor
mcp = FastMCP(
    "ebook-server",
    host=MCP_HOST,
    port=MCP_PORT,
    instructions="""
    This is an ebook library server that provides access to a collection of books.
    Use these tools to browse, read, and search ebooks.
    
    Common workflows:
    1. Use list_books() to see what's available
    2. Use get_book_info() to get chapter details for a specific book
    3. Use get_chapter() to read a specific chapter
    4. Use search_book() to find specific content
    
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
def get_chapter(book_path: str, chapter_number: int) -> str:
    """
    Get the full text content of a specific chapter.
    
    Args:
        book_path: Path to the book (relative to library or full path)
        chapter_number: Chapter number (1-indexed)
    
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
        query: Text to search for (case-insensitive)
    
    Returns:
        JSON array of matches with chapter info and surrounding context
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
        query: Text to search for (case-insensitive)
    
    Returns:
        JSON array of matches with book info, chapter info, and context
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
    
    # Run with SSE transport for Cursor compatibility
    mcp.run(transport="sse")


if __name__ == "__main__":
    main()

