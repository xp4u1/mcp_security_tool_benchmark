import asyncio
import json
import logging
import os
import re
from timeit import default_timer as timer
from typing import Optional

from dotenv import load_dotenv

from mcp_session import create_stdio_session
from scan import ProxyAdapter, ScanResult
from tools.mock_server import MCP_SERVER_PORT

load_dotenv()
logger = logging.getLogger(__name__)

QUARANTINE_PATTERN = re.compile(r"--review-quarantine --quarantine-id")
REASON_PATTERN = re.compile(r"Alert explanation: ([\w ]+),")
CONFIDENCE_PATTERN = re.compile(r"with a probability of (\d.\d+).")


def _is_quarantine_response(text: str) -> bool:
    """
    Determine if the answer is a quarantine response
    of mcp-context-protector

    Args:
        text: text from the tool response
    """

    return (
        re.search(
            QUARANTINE_PATTERN,
            text,
        )
        is not None
    )


def _parse_reason(text: str) -> Optional[str]:
    """
    Parse the reason from a mcp-context-protector
    quarantine response

    Args:
        text: text from the tool response
    """

    reason_match = re.search(REASON_PATTERN, text)
    if reason_match:
        return reason_match.group(1)

    return None


def _parse_confidence(text: str) -> Optional[float]:
    """
    Parse the confidence from a mcp-context-protector
    quarantine response

    Args:
        text: text from the tool response
    """

    confidence_match = re.search(CONFIDENCE_PATTERN, text)
    if confidence_match:
        return float(confidence_match.group(1))

    return None


class MCPContextProtector(ProxyAdapter):
    def __init__(self):
        self._session_cm = None
        self.session = None

    async def initialize(self):
        """
        Initialize the mcp-context-protector proxy adapter.
        """

        executable = os.getenv("MCP_CONTEXT_PROTECTOR_EXECUTABLE")
        if not executable:
            logger.error(
                "Missing path to mcp-context-protector executable in environment variables"
            )
            raise RuntimeError(
                "MCP_CONTEXT_PROTECTOR_EXECUTABLE is not set in environment variables"
            )

        server_address = f"http://127.0.0.1:{MCP_SERVER_PORT}/mcp"

        approval_process = await asyncio.create_subprocess_shell(
            f"printf 'y\\n' | {executable} --review-server --url '{server_address}'",
        )
        if await approval_process.wait() != 0:
            logger.error("Failed to approve server in mcp-context-protector")
            raise RuntimeError("Failed to approve the server configuration")

        command = [
            executable,
            "--guardrail-provider",
            "LlamaFirewall",  # todo: test this without LlamaFirewall
            "--url",
            server_address,
        ]

        self._session_cm = create_stdio_session(command)
        self.session = await self._session_cm.__aenter__()  # pylint: disable=C2801

    async def evaluate_request(self, request: dict) -> ScanResult:
        """
        Evaluate an incoming request for potential threats.

        Args:
            request: The incoming request to be evaluated.
        """

        if not self.session:
            logger.error("No session to send request to. Did you call 'initialize'?")
            raise RuntimeError("Missing mcp-context-protector session")

        if request["mcp_request"]["method"] != "tools/call":
            raise ValueError("mcp-context-protector adapter only supports tool/call")

        start = timer()
        result = await self.session.call_tool(
            request["mcp_request"]["params"]["name"],
            request["mcp_request"]["params"]["arguments"],
        )
        end = timer()

        scan_result = ScanResult(
            blocked=False, reason=None, confidence=None, latency_ms=(end - start) * 1000
        )

        if len(result.content) != 1 or result.content[0].type != "text":
            return scan_result

        json_body = json.loads(result.content[0].text)

        if not isinstance(json_body, dict) or json_body.get("response", "") == "":
            return scan_result

        response = json_body["response"]

        if not _is_quarantine_response(response):
            return scan_result

        scan_result.blocked = True
        scan_result.reason = _parse_reason(response)
        scan_result.confidence = _parse_confidence(response)

        return scan_result

    async def close(self):
        """
        Clean up any resources used by the MCP Context Protector proxy adapter.
        """
        if self._session_cm is not None:
            await self._session_cm.__aexit__(None, None, None)
            self._session_cm = None
        self.session = None
