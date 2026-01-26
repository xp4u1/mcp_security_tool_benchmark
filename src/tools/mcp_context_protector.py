import logging
import os

from dotenv import load_dotenv

from defense_adapter import DefenseAdapter, ScanResult
from mcp_session import create_stdio_session
from tools.mock_server import MCP_SERVER_PORT, MockServer

load_dotenv()
logger = logging.getLogger(__name__)


class MCPContextProtector(DefenseAdapter):
    def __init__(self):
        self.mock_server = None
        self._session_cm = None
        self.session = None

    async def initialize(self):
        """
        Initialize the mcp-context-protector defense adapter.
        """
        self.mock_server = MockServer()
        await self.mock_server.start()

        # mcp-context-protector requires at least one tool to start
        self.mock_server.add_tool(
            name="echo",
            title="Print Tool",
            description="Print input server-side",
            callback=lambda x: print(x),
        )

        executable = os.getenv("MCP_CONTEXT_PROTECTOR_EXECUTABLE")
        if not executable:
            logger.fatal(
                "Missing path to mcp-context-protector executable in environment variables"
            )
            raise ValueError(
                "MCP_CONTEXT_PROTECTOR_EXECUTABLE is not set in environment variables"
            )

        command = [
            executable,
            "--guardrail-provider",
            "LlamaFirewall",  # todo: test this without LlamaFirewall
            "--url",
            f"http://127.0.0.1:{MCP_SERVER_PORT}/mcp",
        ]

        self._session_cm = create_stdio_session(command)
        self.session = await self._session_cm.__aenter__()  # pylint: disable=C2801

    async def evaluate_request(self, request: dict):
        """
        Evaluate an incoming request for potential threats.

        Args:
            request: The incoming request to be evaluated.
        """
        return ScanResult(blocked=False)

    async def close(self):
        """
        Clean up any resources used by the MCP Context Protector defense adapter.
        """
        if self._session_cm is not None:
            await self._session_cm.__aexit__(None, None, None)
            self._session_cm = None
        self.session = None

        if self.mock_server:
            await self.mock_server.stop()
