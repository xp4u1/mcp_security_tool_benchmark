import asyncio
import json
import logging
import os
import tempfile
from pathlib import Path
from timeit import default_timer as timer

from dotenv import load_dotenv

from scan import ScanAdapter, ScanResult

load_dotenv()
logger = logging.getLogger(__name__)


class MCPShield(ScanAdapter):
    def __init__(self, tool_names: list[str]):
        """
        Creates a mcp-shield wrapper. You need to provide a list of tool
        names to search for false negatives since mcp-shield only reports
        findings.

        Args:
            tool_names: List of names of all your server's tools
        """

        self.tool_names = tool_names
        self.repo_path = ""
        self.server_address = ""

    async def initialize(self, server_address: str):
        """
        Initialize the scan adapter.

        Args:
            server_address: The mcp server to be scanned
        """

        path = os.getenv("MCP_SHIELD_REPO_PATH")
        if not path:
            logger.error("Missing path to mcp-shield repo in environment variables")
            raise RuntimeError(
                "MCP_SHIELD_REPO_PATH is not set in environment variables"
            )

        self.repo_path = path
        self.server_address = server_address

    def create_config_file(self, config_path: Path):
        config = {
            "servers": {
                "test": {
                    "url": self.server_address,
                    "type": "http",
                    "headers": {},
                }
            }
        }

        with open(config_path, "w", encoding="utf8") as file:
            json.dump(config, file)

    def parse_results(
        self, vulnerability_report: dict, latency_ms: float
    ) -> dict[str, ScanResult]:
        """
        Args:
            vulnerability_report: Parsed "vulnerabilities" from the mcp-shield output
            latency_ms: Measured latency to include in the scan result
        """

        scan_results = {}

        for tool in self.tool_names:
            finding = vulnerability_report.get(tool)

            scan_results[tool] = (
                ScanResult(
                    blocked=True,
                    reason=json.dumps(finding["detectionDetails"]),
                    latency_ms=latency_ms,
                )
                if finding
                else ScanResult(blocked=False, latency_ms=latency_ms)
            )

        return scan_results

    async def evaluate_tools(self) -> dict[str, ScanResult]:
        """
        Evaluate the mcp server's tools for potential threats.
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            output_path = Path(tmpdir) / "results.json"

            self.create_config_file(config_path)

            start = timer()
            node_process = await asyncio.create_subprocess_shell(
                f"npm start -- --path {config_path} --save-json {output_path}",
                cwd=Path(self.repo_path),
            )
            if await node_process.wait() != 0:
                logger.error("Failed to scan server with mcp-shield")
                raise RuntimeError("Failed to scan the server")
            end = timer()
            latency_ms = (end - start) * 1000

            with open(output_path, "r", encoding="utf8") as file:
                vulnerabilities = json.load(file)[0]["results"]["vulnerabilities"]
                shield_results = {v["tool"]: v for v in vulnerabilities}

        scan_results = {}

        for tool in self.tool_names:
            finding = shield_results.get(tool)

            scan_results[tool] = (
                ScanResult(
                    blocked=True,
                    reason=json.dumps(finding["detectionDetails"]),
                    latency_ms=latency_ms,
                )
                if finding
                else ScanResult(blocked=False, latency_ms=latency_ms)
            )

        return scan_results

    async def close(self):
        """
        Clean up any resources used by the scan adapter.
        """
