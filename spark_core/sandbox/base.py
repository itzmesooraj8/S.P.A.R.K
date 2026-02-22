from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class ExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_ms: int = 0
    truncated: bool = False
    
    @property
    def success(self) -> bool:
        return self.exit_code == 0

class ExecutionEnvironment(ABC):
    @abstractmethod
    async def setup(self) -> bool:
        """Initialize the sandbox environment."""
        pass
        
    @abstractmethod
    async def run_command(self, cmd: str) -> ExecutionResult:
        """Run a command inside the sandbox."""
        pass
        
    @abstractmethod
    async def read_file(self, path: str) -> str:
        """Read a file from the sandbox."""
        pass

    @abstractmethod
    async def write_file(self, path: str, content: str) -> bool:
        """Write a file inside the sandbox."""
        pass
        
    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """Delete a file inside the sandbox."""
        pass
        
    @abstractmethod
    async def list_dir(self, path: str) -> str:
        """List contents of a directory inside the sandbox."""
        pass
        
    @abstractmethod
    async def snapshot(self, name: str) -> bool:
        """Create a snapshot of the current environment state."""
        pass
        
    @abstractmethod
    async def rollback(self, name: str) -> bool:
        """Revert the environment to a previous snapshot."""
        pass
        
    @abstractmethod
    async def teardown(self) -> bool:
        """Destroy the sandbox environment and clean up."""
        pass
