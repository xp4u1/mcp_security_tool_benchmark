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
    async def initialize(self):
        """
        Initialize the scan adapter.
        """

    @abstractmethod
    async def evaluate_server(self, server_address: str) -> ScanResult:
        """
        Evaluate an mcp server for potential threats.

        Args:
            request: The incoming request to be evaluated.
        """

    @abstractmethod
    async def close(self):
        """
        Clean up any resources used by the scan adapter.
        """
