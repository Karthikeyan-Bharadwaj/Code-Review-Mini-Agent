"""Node registry and base classes for workflow execution."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from app.engine import ExecutionContext
from uuid import uuid4

from app.models import NodeDefinition, EdgeDefinition


class NodeResult:
    """Result of node execution."""
    
    def __init__(self, success: bool = True, error_message: Optional[str] = None, 
                 next_nodes: Optional[List[str]] = None):
        """Initialize node result."""
        self.success = success
        self.error_message = error_message
        self.next_nodes = next_nodes or []


class Node(ABC):
    """Base class for workflow nodes."""
    
    def __init__(self, node_id: str, config: Optional[Dict[str, Any]] = None):
        """Initialize node."""
        self.node_id = node_id
        self.config = config or {}
        self.timeout = self.config.get('timeout', 30.0)
    
    @abstractmethod
    async def execute(self, context: 'ExecutionContext') -> NodeResult:
        """Execute the node logic."""
        pass
    
    async def execute_with_timeout(self, context: 'ExecutionContext') -> NodeResult:
        """Execute node with timeout protection."""
        try:
            return await asyncio.wait_for(self.execute(context), timeout=self.timeout)
        except asyncio.TimeoutError:
            error_msg = f"Node {self.node_id} timed out after {self.timeout} seconds"
            await context.log(self.node_id, error_msg, "ERROR")
            return NodeResult(success=False, error_message=error_msg)
        except Exception as e:
            error_msg = f"Node {self.node_id} failed with exception: {str(e)}"
            await context.log(self.node_id, error_msg, "ERROR", {"exception": str(e)})
            return NodeResult(success=False, error_message=error_msg)


class NodeRegistry:
    """Registry for managing node types and instances."""
    
    def __init__(self):
        """Initialize node registry."""
        self._node_types: Dict[str, type] = {}
        self._nodes: Dict[str, Node] = {}
    
    def register_node_type(self, node_type: str, node_class: type):
        """Register a node type."""
        self._node_types[node_type] = node_class
    
    def create_node(self, definition: NodeDefinition) -> Node:
        """Create a node from definition."""
        if definition.type not in self._node_types:
            raise ValueError(f"Unknown node type: {definition.type}")
        
        node_class = self._node_types[definition.type]
        node = node_class(definition.id, definition.config)
        self._nodes[definition.id] = node
        return node
    
    def get_node(self, node_id: str) -> Optional[Node]:
        """Get node by ID."""
        return self._nodes.get(node_id)


# Global node registry
node_registry = NodeRegistry()