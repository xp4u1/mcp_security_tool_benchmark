"""
Adapter for https://github.com/cisco-ai-defense/mcp-scannerner

For LLM configuration (env variables) see:
https://github.com/cisco-ai-defense/mcp-scannerner/blob/main/docs/llm-providers.md
"""

import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from timeit import default_timer as timer
from typing import Literal

from dotenv import load_dotenv

from scan import ScanAdapter, ScanResult

load_dotenv()
logger = logging.getLogger(__name__)

Analyzer = Literal["yara", "llm", "api"]


class MCPScanner(ScanAdapter):
    def __init__(self, analyzers: list[Analyzer]):
        """
        Creates a mcp-scannerner wrapper.

        Args:
            analyzers: mcp-scanner analyzers that should be used for the scans
        """

        self.repo_path = ""
        self.server_address = ""
        self.analyzers = ",".join(analyzers)

    async def initialize(self, server_address: str):
        """
        Initialize the scan adapter.

        Args:
            server_address: The mcp server to be scanned
        """

        path = os.getenv("MCP_SCANNER_REPO_PATH")
        if not path:
            logger.error("Missing path to mcp-scannerner repo in environment variables")
            raise RuntimeError(
                "MCP_SCANNER_REPO_PATH is not set in environment variables"
            )

        self.repo_path = path
        self.server_address = server_address

    async def evaluate_tools(self) -> dict[str, ScanResult]:
        """
        Evaluate the mcp server's tools for potential threats.
        All tools are scanned at once. Therefore the scan results
        contain the average: scan_time / tool_count
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.json"

            start = timer()
            node_process = await asyncio.create_subprocess_shell(
                (
                    f"uv run mcp-scanner --analyzers {self.analyzers}"
                    f" --server-url {self.server_address} --raw > {output_path}"
                ),
                cwd=Path(self.repo_path),
            )
            if await node_process.wait() != 0:
                logger.error("Failed to scan server with mcp-scanner")
                raise RuntimeError("Failed to scan the server")
            end = timer()

            with open(output_path, "r", encoding="utf8") as file:
                scan_report = json.load(file)

        scan_results = {}
        latency_ms = ((end - start) * 1000) / len(scan_report)

        for tool in scan_report:
            assert tool["status"] == "completed"
            findings = tool["findings"]

            scan_results[tool["tool_name"]] = ScanResult(
                blocked=not tool["is_safe"],
                reason=json.dumps(findings),
                latency_ms=latency_ms,
            )

        return scan_results

    async def close(self):
        """
        Clean up any resources used by the scan adapter.
        """
