"""Feishu Wiki uploader - creates wiki nodes and populates them with document content."""

from datetime import datetime

from src.feishu_client import FeishuClient
from src.markdown_to_blocks import markdown_to_feishu_blocks


class FeishuUploader:
    """Creates a wiki node and populates it with document content."""

    def __init__(self, config: dict):
        self.config = config
        self.client = FeishuClient(config)
        self.space_id = config["feishu"]["wiki_space_id"]
        self.parent_node_token = config["feishu"].get("parent_node_token", "")

    def upload(self, title: str, markdown_content: str) -> str:
        """
        Create a wiki node containing a docx document with the given content.
        Returns the wiki URL.
        """
        # Step 1: Create wiki node (obj_type="docx")
        node_info = self._create_wiki_node(title)
        node_token = node_info["node_token"]
        document_id = node_info["obj_token"]  # The underlying docx document ID

        # Step 2: Convert markdown to Feishu blocks
        blocks = markdown_to_feishu_blocks(markdown_content)
        print(f"    Converted markdown to {len(blocks)} Feishu blocks")

        # Step 3: Insert blocks into the document
        # The document root block ID == document_id
        self._insert_blocks(document_id, parent_block_id=document_id, blocks=blocks)

        # Construct the wiki URL
        base = self.config["feishu"]["base_url"].replace("open.", "")
        # Typical URL: https://your-domain.feishu.cn/wiki/{node_token}
        wiki_url = f"{base}/wiki/{node_token}"
        return wiki_url

    def _create_wiki_node(self, title: str) -> dict:
        """Create a new wiki node and return the node info."""
        body = {
            "obj_type": "docx",
            "node_type": "origin",
            "title": title,
        }
        if self.parent_node_token:
            body["parent_node_token"] = self.parent_node_token

        data = self.client.request(
            "POST",
            f"/open-apis/wiki/v2/spaces/{self.space_id}/nodes",
            json=body,
        )
        return data["data"]["node"]

    def _insert_blocks(self, document_id: str, parent_block_id: str, blocks: list):
        """Insert blocks as children. Feishu limits ~50 blocks per request."""
        chunk_size = 50
        for i in range(0, len(blocks), chunk_size):
            chunk = blocks[i : i + chunk_size]
            self.client.request(
                "POST",
                f"/open-apis/docx/v1/documents/{document_id}/blocks/{parent_block_id}/children",
                json={"children": chunk, "index": -1},
            )