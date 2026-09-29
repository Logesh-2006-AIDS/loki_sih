import os
import uuid
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO
from app.core.config import settings


class BaseStorageService(ABC):
    @abstractmethod
    def save_file(self, file_obj: BinaryIO, filename: str, subfolder: str = "") -> str:
        """Saves file and returns relative or absolute storage path."""
        pass

    @abstractmethod
    def get_file_path(self, storage_path: str) -> Path:
        """Returns the resolved local filesystem Path."""
        pass

    @abstractmethod
    def delete_file(self, storage_path: str) -> bool:
        """Deletes file from storage."""
        pass


class LocalStorageService(BaseStorageService):
    def __init__(self, base_path: str = settings.STORAGE_PATH):
        self.base_path = Path(base_path).resolve()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def save_file(self, file_obj: BinaryIO, filename: str, subfolder: str = "") -> str:
        target_dir = self.base_path / subfolder if subfolder else self.base_path
        target_dir.mkdir(parents=True, exist_ok=True)

        # Generate unique storage filename to avoid collisions
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        target_path = target_dir / unique_name

        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(file_obj, buffer)

        # Return relative storage path
        return str(target_path.relative_to(self.base_path))

    def get_file_path(self, storage_path: str) -> Path:
        clean_path = storage_path.lstrip("/\\")
        if clean_path.startswith("storage/") or clean_path.startswith("storage\\"):
            clean_path = clean_path[len("storage/"):]
        return self.base_path / clean_path

    def delete_file(self, storage_path: str) -> bool:
        path = self.get_file_path(storage_path)
        if path.exists() and path.is_file():
            path.unlink()
            return True
        return False
