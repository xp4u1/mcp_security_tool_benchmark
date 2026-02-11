import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from uuid import uuid4

from dataclasses_json import dataclass_json

logger = logging.getLogger(__name__)

DATASET_PATH = "data/dataset.json"


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


@dataclass_json
@dataclass
class Scenario:
    id: str
    dataset: str
    server: ServerData


class DatasetLoader(ABC):
    @abstractmethod
    def load(self) -> list[ServerData]:
        """
        Load the dataset
        """


def save_dataset(loaders: list[DatasetLoader]):
    """
    Generate the dataset scenarios using the given dataset loaders
    and save it as json file
    """

    logger.info("Creating dataset")
    dataset = [
        Scenario(id=str(uuid4()), dataset=dataset.__module__, server=server_data)
        for dataset in loaders
        for server_data in dataset.load()
    ]

    logger.info("Saving dataset to '%s'", DATASET_PATH)
    with open(DATASET_PATH, "w", encoding="utf8") as file:
        json.dump([scenario.to_dict() for scenario in dataset], file)


def load_dataset() -> list[Scenario]:
    logger.info("Loading dataset from '%s'", DATASET_PATH)

    with open(DATASET_PATH, "r", encoding="utf8") as file:
        return [Scenario.from_dict(scenario) for scenario in json.load(file)]
