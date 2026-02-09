import json
import logging
import os
from timeit import default_timer as timer

import httpx
from dotenv import load_dotenv

from dataset import ServerData
from scan import ScanAdapter, ScanResult

load_dotenv()
logger = logging.getLogger(__name__)


class MCPGuard(ScanAdapter):
    def __init__(self, server_data: ServerData):
        """
        Creates a mcg-guard wrapper. You need to provide a list of tool
        names to search for false negatives since mcg-guard only reports
        findings.

        Args:
            server_data: MCP server content
        """

        self.api_server_url = None
        self.server_data = server_data
        self.server_address = ""
        self.tools = []

    async def initialize(self, server_address: str):
        """
        Initialize the scan adapter.

        Args:
            server_address: The mcp server to be scanned
        """

        self.server_address = server_address

        self.api_server_url = os.getenv("MCP_GUARD_API_URL")
        if not self.api_server_url:
            logger.error("Missing url to mcp-guard api in environment variables")
            raise RuntimeError("MCP_GUARD_API_URL is not set in environment variables")

        logging.getLogger("httpx").setLevel("WARNING")

    async def evaluate_tools(self) -> dict[str, ScanResult]:
        """
        Evaluate the mcp server's tools for potential threats.
        """

        result = {}

        for tool in self.server_data.tools:
            start = timer()
            response = httpx.post(
                f"{self.api_server_url}/guardrail/scan",
                content=json.dumps(
                    {
                        "tool_name": tool.name,
                        "tool_description": tool.description,
                        "servers": [{"url": self.server_address}],
                        "tool_input_schema": {},  # todo: real input schema
                    }
                ),
            )
            end = timer()
            latency_ms = (end - start) * 1000

            response.raise_for_status()
            response_data = response.json()

            result[tool.name] = ScanResult(
                blocked=not response_data["allowed"],
                reason=response.text,
                latency_ms=latency_ms,
            )

        return result

    async def close(self):
        """
        Clean up any resources used by the scan adapter.
        """
