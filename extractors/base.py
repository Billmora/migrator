from abc import ABC, abstractmethod
from typing import Generator, Any, Tuple

class BaseExtractor(ABC):
    """
    Abstract Base Class for all extractors.
    """
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        
    @abstractmethod
    def extract(self) -> Generator[Tuple[str, dict[str, Any]], None, None]:
        """
        Reads the data source and yields records.
        
        Yields:
            Tuple[str, dict]: A tuple containing the table/entity name and the record as a dictionary.
        """
        pass
