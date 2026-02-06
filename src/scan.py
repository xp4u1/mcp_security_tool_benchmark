from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class ScanResult:
    blocked: bool
    reason: Optional[str] = None
    confidence: Optional[float] = None
    latency_ms: Optional[float] = None


class ProxyAdapter(ABC):
    @abstractmethod
    async def initialize(self):
        """
        Initialize the proxy adapter.
        """

    @abstractmethod
    async def evaluate_request(self, request: dict) -> ScanResult:
        """
        Evaluate an incoming request for potential threats.

        Args:
            request: The incoming request to be evaluated.
        """

    @abstractmethod
    async def close(self):
        """
        Clean up any resources used by the proxy adapter.
        """


class ScanAdapter(ABC):
    @abstractmethod
    async def initialize(self, server_address: str):
        """
        Initialize the scan adapter.

        Args:
            server_address: The mcp server to be scanned
        """

    @abstractmethod
    async def evaluate_tools(self) -> dict[str, ScanResult]:
        """
        Evaluate the mcp server's tools for potential threats.
        """

    @abstractmethod
    async def close(self):
        """
        Clean up any resources used by the scan adapter.
        """
