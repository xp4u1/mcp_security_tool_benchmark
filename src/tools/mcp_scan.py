import asyncio
import json
import logging
import tempfile
from pathlib import Path
from timeit import default_timer as timer

from dotenv import load_dotenv

from scan import ScanAdapter, ScanResult

load_dotenv()
logger = logging.getLogger(__name__)


class MCPScan(ScanAdapter):
    def __init__(self):
        """
        Creates a mcp-scan wrapper.
        """

        self.server_address = ""

    async def initialize(self, server_address: str):
        """
        Initialize the scan adapter.

        Args:
            server_address: The mcp server to be scanned
        """

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

    async def evaluate_tools(self) -> dict[str, ScanResult]:
        """
        Evaluate the mcp server's tools for potential threats.
        All tools are scanned at once. Therefore the scan results
        contain the average: scan_time / tool_count
        """

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            output_path = Path(tmpdir) / "results.json"

            self.create_config_file(config_path)

            start = timer()
            node_process = await asyncio.create_subprocess_shell(
                f"uvx mcp-scan {config_path} --json --full-toxic-flows --opt-out > {output_path}",
                cwd=Path(tmpdir),
            )
            if await node_process.wait() != 0:
                logger.error("Failed to scan server with mcp-scan")
                raise RuntimeError("Failed to scan the server")
            end = timer()

            with open(output_path, "r", encoding="utf8") as file:
                scan_report = json.load(file)[str(config_path)]

        if error := scan_report["error"]:
            logger.error("Scan failed: %s", error)
            raise RuntimeError("Failed to scan the server")

        tools = scan_report["servers"][0]["signature"]["tools"]
        issues = scan_report["issues"]
        latency_ms = ((end - start) * 1000) / len(tools)

        scan_results = {}
        for index, tool in enumerate(tools):
            tool_issues = [
                issue for issue in issues if issue["reference"] == [0, index]
            ]

            scan_results[tool["name"]] = ScanResult(
                blocked=any(issue["code"].startswith("E") for issue in tool_issues),
                reason=json.dumps(tool_issues),
                latency_ms=latency_ms,
            )

        return scan_results

    async def close(self):
        """
        Clean up any resources used by the scan adapter.
        """
