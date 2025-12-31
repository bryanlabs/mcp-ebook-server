# MCP Ebook Server

An MCP (Model Context Protocol) server that provides AI assistants with direct access to your ebook library. Works with Claude in Cursor, and other MCP-compatible clients.

[![Install in Cursor](https://img.shields.io/badge/Install%20in-Cursor-blue?style=for-the-badge&logo=cursor)](cursor://anysphere.cursor-deeplink/mcp/install?name=ebooks&config=eyJ1cmwiOiJodHRwOi8vbG9jYWxob3N0OjgwODAvc3NlIn0K)

> **Note:** The one-click install assumes the server is running on `localhost:8080`. For remote servers, see [Client Integration](#client-integration).

## Features

- **List books** in your library with metadata (title, author, language)
- **Read chapters** individually or in ranges
- **Search** within books or across your entire library
- **EPUB support** with automatic text extraction

## Why Use This Instead of LLM Training Data?

LLMs like Claude have read millions of books during training, but they don't actually *have* those books—they have a compressed neural representation of patterns and themes. This creates real limitations:

| Question Type | LLM Training Data | MCP Ebook Server |
|--------------|-------------------|------------------|
| "What's the 10th word of chapter 2?" | ❌ Cannot answer | ✅ Exact answer |
| "Quote the opening paragraph" | ⚠️ Often paraphrased or hallucinated | ✅ Verbatim text |
| "How many times is 'magic' mentioned?" | ❌ Guesses | ✅ Precise count |
| "What happens in chapter 5?" | ⚠️ May confuse with similar books | ✅ Actual content |
| "Does this book mention X?" | ⚠️ Uncertain, may hallucinate | ✅ Searchable proof |

**The core problem:** LLMs retain the *gist* of books—major plot points, famous quotes, general themes—but lose precise details. When asked about specifics they don't know, they often hallucinate plausible-sounding answers rather than admitting uncertainty.

**The solution:** This MCP server gives AI direct access to the actual source text. Instead of guessing, the AI can read the exact chapter, search for specific terms, and cite real passages. No hallucinations, just the book.

## Installation

### Docker (Recommended)

```bash
docker run -p 8080:8080 -v /path/to/your/ebooks:/ebooks ghcr.io/bryanlabs/mcp-ebook-server:latest
```

### Docker Compose

```yaml
services:
  mcp-ebook-server:
    image: ghcr.io/bryanlabs/mcp-ebook-server:latest
    ports:
      - "8080:8080"
    volumes:
      - /path/to/your/ebooks:/ebooks:ro
```

### pip

```bash
pip install git+https://github.com/bryanlabs/mcp-ebook-server.git
mcp-ebook-server --library-path /path/to/your/ebooks
```

### From Source

```bash
git clone https://github.com/bryanlabs/mcp-ebook-server.git
cd mcp-ebook-server
pip install -e .
mcp-ebook-server
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `EBOOK_LIBRARY_PATH` | `/ebooks` | Path to your ebook directory |
| `MCP_HOST` | `0.0.0.0` | Host to bind the server |
| `MCP_PORT` | `8080` | Port for the SSE endpoint |

## Client Integration

Once the server is running, connect your AI client to `http://localhost:8080/sse` (or your server's URL).

### Cursor IDE

**One-click install (localhost):**

[![Install in Cursor](https://img.shields.io/badge/Install%20in-Cursor-blue?logo=cursor)](cursor://anysphere.cursor-deeplink/mcp/install?name=ebooks&config=eyJ1cmwiOiJodHRwOi8vbG9jYWxob3N0OjgwODAvc3NlIn0K)

**Or manually edit** `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "ebooks": {
      "type": "sse",
      "url": "http://localhost:8080/sse"
    }
  }
}
```

Reload Cursor: `Cmd+Shift+P` → "Developer: Reload Window"

---

### Claude Desktop

Edit the config file:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ebooks": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "/path/to/your/ebooks:/ebooks:ro",
        "ghcr.io/bryanlabs/mcp-ebook-server:latest"
      ]
    }
  }
}
```

Or if running the server separately (Docker/remote):

```json
{
  "mcpServers": {
    "ebooks": {
      "type": "sse",
      "url": "http://localhost:8080/sse"
    }
  }
}
```

Restart Claude Desktop to apply changes.

---

### Claude Code (CLI)

```bash
# Add the server
claude mcp add ebooks --transport sse --url http://localhost:8080/sse

# Verify it's added
claude mcp list

# Or import from Claude Desktop if already configured there
claude mcp add-from-claude-desktop
```

---

### VS Code (with Copilot/Continue)

For VS Code with MCP-compatible extensions, create `.vscode/mcp.json` in your workspace:

```json
{
  "mcpServers": {
    "ebooks": {
      "type": "sse",
      "url": "http://localhost:8080/sse"
    }
  }
}
```

Or use the Command Palette: `MCP: Add Server` → select SSE → enter the URL.

---

### ChatGPT Desktop

Edit the config file:
- **macOS:** `~/Library/Application Support/ChatGPT/chatgpt_desktop_config.json`
- **Windows:** `%APPDATA%\ChatGPT\chatgpt_desktop_config.json`

```json
{
  "mcpServers": {
    "ebooks": {
      "type": "sse",
      "url": "http://localhost:8080/sse"
    }
  }
}
```

Restart ChatGPT Desktop to apply changes.

---

### Remote/Cloud Deployment

If running on a remote server or Kubernetes cluster, replace `localhost:8080` with your server's address:

```json
{
  "mcpServers": {
    "ebooks": {
      "type": "sse",
      "url": "http://your-server-ip:32080/sse"
    }
  }
}
```

## Available Tools

### `list_books()`
Lists all ebooks in your library with metadata.

**Example:** "What books do I have?"

### `get_book_info(book_path)`
Get detailed information about a book including chapter list.

**Example:** "How many chapters are in The Magicians?"

### `get_chapter(book_path, chapter_number)`
Read a specific chapter's full text.

**Example:** "Read chapter 1 of The Magicians"

### `get_chapters_range(book_path, start_chapter, end_chapter)`
Read multiple chapters at once.

**Example:** "Get chapters 1 through 3 of The Magicians"

### `search_book(book_path, query)`
Search for text within a specific book.

**Example:** "Find all mentions of 'magic' in The Magicians"

### `search_library(query)`
Search across all books in your library.

**Example:** "Search all my books for 'dragon'"

## Supported Formats

| Format | Status |
|--------|--------|
| EPUB | Fully supported |
| MOBI | Requires conversion to EPUB |
| AZW3 | Requires conversion to EPUB |
| PDF | Not supported |

## Example Queries

Once configured, you can ask your AI assistant questions like:

- "What books do I have in my library?"
- "Without spoilers past chapter 3, who is Quentin in The Magicians?"
- "Find all mentions of 'Brakebills' in chapter 1"
- "Summarize what happens in chapters 1-3 of The Magicians"

## Kubernetes Deployment

Example Kubernetes manifests:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-ebook-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mcp-ebook-server
  template:
    metadata:
      labels:
        app: mcp-ebook-server
    spec:
      containers:
        - name: mcp-ebook-server
          image: ghcr.io/bryanlabs/mcp-ebook-server:latest
          ports:
            - containerPort: 8080
          env:
            - name: EBOOK_LIBRARY_PATH
              value: "/ebooks"
          volumeMounts:
            - name: ebooks
              mountPath: /ebooks
              readOnly: true
      volumes:
        - name: ebooks
          persistentVolumeClaim:
            claimName: ebooks-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: mcp-ebook-server
spec:
  type: NodePort
  selector:
    app: mcp-ebook-server
  ports:
    - port: 8080
      targetPort: 8080
      nodePort: 32080
```

## License

MIT License - see [LICENSE](LICENSE) for details.

