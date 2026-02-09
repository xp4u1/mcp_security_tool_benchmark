import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

from dataclasses_json import dataclass_json

logger = logging.getLogger(__name__)


@dataclass_json
@dataclass
class ToolData:
    name: str
    description: str
    malicious: bool
    category: str
    return_value: str = ""


@dataclass_json
@dataclass
class ServerData:
    name: str
    instruction: str
    tools: list[ToolData]


class Dataset(ABC):
    @abstractmethod
    def load(self) -> list[ServerData]:
        """
        Load the dataset
        """
