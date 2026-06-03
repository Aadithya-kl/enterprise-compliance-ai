"""
Notion MCP source.
Fetches pages from a configured Notion database and converts them to text.

Configuration (in .env):
    NOTION_API_TOKEN=<Notion integration token>
    NOTION_DATABASE_ID=<database ID from Notion URL>

Requires: pip install notion-client
"""

from app.core.config import settings
from app.core.logging import get_logger
from app.mcp.base import MCPDocument, MCPSource

logger = get_logger(__name__)


class NotionMCPSource(MCPSource):
    """Fetches compliance documents from a Notion database."""

    @property
    def source_name(self) -> str:
        return "notion"

    def is_configured(self) -> bool:
        return bool(settings.NOTION_API_TOKEN and settings.NOTION_DATABASE_ID)

    def fetch_documents(self) -> list[MCPDocument]:
        if not self.is_configured():
            logger.info(
                "Notion MCP: not configured "
                "(NOTION_API_TOKEN or NOTION_DATABASE_ID missing). Skipping."
            )
            return []

        try:
            from notion_client import Client
        except ImportError:
            logger.warning(
                "Notion MCP: notion-client not installed. "
                "Run: pip install notion-client"
            )
            return []

        try:
            client = Client(auth=settings.NOTION_API_TOKEN)
            pages = self._list_pages(client)
        except Exception as exc:
            logger.error(f"Notion MCP: failed to list pages: {exc}")
            return []

        documents: list[MCPDocument] = []
        for page in pages:
            try:
                page_id = page["id"]
                title = self._extract_title(page)
                text = self._extract_page_text(client, page_id)

                if not text.strip():
                    logger.warning(f"Notion MCP: page '{title}' has no text, skipping.")
                    continue

                documents.append(
                    MCPDocument(
                        title=title,
                        content=text,
                        source=self.source_name,
                        document_type=self._infer_type(title),
                        metadata={
                            "notion_page_id": page_id,
                            "title": title,
                        },
                    )
                )
                logger.info(f"Notion MCP: loaded page '{title}'")
            except Exception as exc:
                logger.error(
                    f"Notion MCP: failed to process page: {exc}", exc_info=True
                )

        logger.info(f"Notion MCP: fetched {len(documents)} pages.")
        return documents

    def _list_pages(self, client) -> list[dict]:
        """Query all pages from the configured Notion database."""
        results = []
        cursor = None
        while True:
            kwargs = {
                "database_id": settings.NOTION_DATABASE_ID,
                "page_size": 100,
            }
            if cursor:
                kwargs["start_cursor"] = cursor

            response = client.databases.query(**kwargs)
            results.extend(response.get("results", []))

            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        return results

    def _extract_title(self, page: dict) -> str:
        """Extract the title property from a Notion page."""
        props = page.get("properties", {})
        for prop in props.values():
            if prop.get("type") == "title":
                title_parts = prop.get("title", [])
                return "".join(part.get("plain_text", "") for part in title_parts)
        return f"Page {page['id']}"

    def _extract_page_text(self, client, page_id: str) -> str:
        """Recursively extract all text blocks from a Notion page."""
        blocks = []
        cursor = None

        while True:
            kwargs = {"block_id": page_id, "page_size": 100}
            if cursor:
                kwargs["start_cursor"] = cursor

            response = client.blocks.children.list(**kwargs)
            blocks.extend(response.get("results", []))

            if not response.get("has_more"):
                break
            cursor = response.get("next_cursor")

        text_parts: list[str] = []
        for block in blocks:
            block_type = block.get("type", "")
            block_data = block.get(block_type, {})
            rich_text = block_data.get("rich_text", [])
            text = "".join(part.get("plain_text", "") for part in rich_text)
            if text:
                text_parts.append(text)

        return "\n".join(text_parts)

    def _infer_type(self, title: str) -> str:
        lower = title.lower()
        if "policy" in lower:
            return "policy"
        if "regulation" in lower or "regulatory" in lower:
            return "regulation"
        return "general"
