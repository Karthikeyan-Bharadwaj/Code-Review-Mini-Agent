"""Graph execution engine for workflow processing."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Any
from uuid import uuid4

from .models import GraphDefinition, ExecutionState, RunStatus, RunResult, LogEntry
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from registry import Node, NodeRegistry, node_registry


class ExecutionContext:
    """Manages state and logging during workflow execution."""
    
    def __init__(self, run_id: str, initial_state: ExecutionState):
        """Initialize execution context."""
        self.run_id = run_id
        self.state = initial_state.copy(deep=True)
        self.logs: List[LogEntry] = []
        self.status = RunStatus.PENDING
        self.current_node: Optional[str] = None
        self.created_at = datetime.now()
        self.completed_at: Optional[datetime] = None
        self.error_message: Optional[str] = None
        self._lock = asyncio.Lock()
    
    async def log(self, node_id: str, message: str, level: str = "INFO", data: Optional[Dict[str, Any]] = None):
        """Add a log entry."""
        async with self._lock:
            entry = LogEntry(
                timestamp=datetime.now(),
                node_id=node_id,
                level=level,
                message=message,
                data=data
            )
            self.logs.append(entry)
    
    async def update_state(self, updates: Dict[str, Any]):
        """Update execution state."""
        async with self._lock:
            for key, value in updates.items():
                if hasattr(self.state, key):
                    setattr(self.state, key, value)
                else:
                    self.state.custom_data[key] = value
    
    async def set_status(self, status: RunStatus, error_message: Optional[str] = None):
        """Update run status."""
        async with self._lock:
            self.status = status
            if error_message:
                self.error_message = error_message
            if status in [RunStatus.COMPLETED, RunStatus.ERROR, RunStatus.TIMEOUT]:
                self.completed_at = datetime.now()
    
    async def set_current_node(self, node_id: Optional[str]):
        """Set the currently executing node."""
        async with self._lock:
            self.current_node = node_id
    
    async def increment_iteration(self):
        """Increment the iteration counter."""
        async with self._lock:
            self.state.iteration_count += 1
    
    def get_tool(self, tool_name: str):
        """Get a tool function from the tool registry."""
        # Import here to avoid circular imports
        import sys
        import os
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from workflows import get_tool
        return get_tool(tool_name)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for serialization."""
        return {
            "run_id": self.run_id,
            "status": self.status.value,
            "current_node": self.current_node,
            "iteration_count": self.state.iteration_count,
            "state": self.state.dict(),
            "logs": [log.dict() for log in self.logs],
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message
        }


class ContextManager:
    """Manages execution contexts for multiple runs."""
    
    def __init__(self):
        """Initialize context manager."""
        self._contexts: Dict[str, ExecutionContext] = {}
        self._lock = asyncio.Lock()
    
    async def create_context(self, initial_state: ExecutionState) -> ExecutionContext:
        """Create a new execution context."""
        run_id = str(uuid4())
        context = ExecutionContext(run_id, initial_state)
        
        async with self._lock:
            self._contexts[run_id] = context
        
        return context
    
    async def get_context(self, run_id: str) -> Optional[ExecutionContext]:
        """Get execution context by run ID."""
        async with self._lock:
            return self._contexts.get(run_id)


class Edge:
    """Represents a connection between nodes."""
    
    def __init__(self, from_node: str, to_node: str, condition: Optional[str] = None):
        """Initialize edge."""
        self.from_node = from_node
        self.to_node = to_node
        self.condition = condition
    
    def should_traverse(self, context: ExecutionContext) -> bool:
        """Check if this edge should be traversed."""
        if not self.condition:
            return True
        
        try:
            # Simple condition evaluation
            condition = self.condition.strip()
            
            if condition.startswith('state.'):
                parts = condition.split(' ', 2)
                if len(parts) >= 3:
                    field_path = parts[0]
                    operator = parts[1]
                    value_str = parts[2]
                    
                    field_name = field_path.replace('state.', '')
                    if hasattr(context.state, field_name):
                        field_value = getattr(context.state, field_name)
                    else:
                        field_value = context.state.custom_data.get(field_name)
                    
                    try:
                        if '.' in value_str:
                            target_value = float(value_str)
                        else:
                            target_value = int(value_str)
                    except ValueError:
                        target_value = value_str.strip('"\'')
                    
                    if operator == '>=':
                        return field_value >= target_value
                    elif operator == '<=':
                        return field_value <= target_value
                    elif operator == '>':
                        return field_value > target_value
                    elif operator == '<':
                        return field_value < target_value
                    elif operator == '==':
                        return field_value == target_value
                    elif operator == '!=':
                        return field_value != target_value
            
            return True
        except Exception:
            return True


# Global context manager instance
context_manager = ContextManager()


class Graph:
    """Represents a workflow graph."""
    
    def __init__(self, graph_id: str, definition: GraphDefinition):
        """Initialize graph.
        
        Args:
            graph_id: Unique graph identifier
            definition: Graph definition
        """
        self.graph_id = graph_id
        self.definition = definition
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._build_graph()
    
    def _build_graph(self):
        """Build graph from definition."""
        # Create nodes
        for node_def in self.definition.nodes.values():
            node = node_registry.create_node(node_def)
            self.nodes[node_def.id] = node
        
        # Create edges
        for edge_def in self.definition.edges:
            edge = Edge(edge_def.from_node, edge_def.to_node, edge_def.condition)
            self.edges.append(edge)
    
    def get_next_nodes(self, current_node: str, context: ExecutionContext) -> List[str]:
        """Get next nodes to execute based on edges and conditions.
        
        Args:
            current_node: Current node ID
            context: Execution context
            
        Returns:
            List of next node IDs
        """
        next_nodes = []
        for edge in self.edges:
            if edge.from_node == current_node and edge.should_traverse(context):
                next_nodes.append(edge.to_node)
        return next_nodes
    
    def validate(self) -> List[str]:
        """Validate graph structure.
        
        Returns:
            List of validation errors
        """
        errors = []
        
        # Check that start node exists
        if self.definition.start_node not in self.definition.nodes:
            errors.append(f"Start node '{self.definition.start_node}' not found in nodes")
        
        # Check that all edge nodes exist
        for edge_def in self.definition.edges:
            if edge_def.from_node not in self.definition.nodes:
                errors.append(f"Edge from_node '{edge_def.from_node}' not found in nodes")
            if edge_def.to_node not in self.definition.nodes:
                errors.append(f"Edge to_node '{edge_def.to_node}' not found in nodes")
        
        # Check for cycles (simple detection)
        visited = set()
        rec_stack = set()
        
        def has_cycle(node_id: str) -> bool:
            if node_id in rec_stack:
                return True
            if node_id in visited:
                return False
            
            visited.add(node_id)
            rec_stack.add(node_id)
            
            # Get all outgoing edges
            for edge in self.edges:
                if edge.from_node == node_id:
                    if has_cycle(edge.to_node):
                        return True
            
            rec_stack.remove(node_id)
            return False
        
        # Only check for cycles if we don't have loop control
        # (loops are allowed with proper termination conditions)
        
        return errors


class GraphEngine:
    """Main graph execution engine."""
    
    def __init__(self):
        """Initialize graph engine."""
        self._graphs: Dict[str, Graph] = {}
        self._lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)
    
    async def create_graph(self, definition: GraphDefinition) -> str:
        """Create a new graph from definition.
        
        Args:
            definition: Graph definition
            
        Returns:
            Unique graph ID
            
        Raises:
            ValueError: If graph definition is invalid
        """
        # Generate unique graph ID
        graph_id = str(uuid4())
        
        # Create and validate graph
        graph = Graph(graph_id, definition)
        errors = graph.validate()
        if errors:
            raise ValueError(f"Graph validation failed: {'; '.join(errors)}")
        
        # Store graph
        async with self._lock:
            self._graphs[graph_id] = graph
        
        self.logger.info(f"Created graph {graph_id} with {len(definition.nodes)} nodes")
        return graph_id
    
    async def get_graph(self, graph_id: str) -> Optional[Graph]:
        """Get graph by ID.
        
        Args:
            graph_id: Graph identifier
            
        Returns:
            Graph instance or None if not found
        """
        async with self._lock:
            return self._graphs.get(graph_id)
    
    async def execute_graph(self, graph_id: str, initial_state: ExecutionState, 
                          sync: bool = False) -> RunResult:
        """Execute a graph workflow.
        
        Args:
            graph_id: Graph identifier
            initial_state: Initial execution state
            sync: Whether to run synchronously
            
        Returns:
            Run result
            
        Raises:
            ValueError: If graph not found
        """
        graph = await self.get_graph(graph_id)
        if not graph:
            raise ValueError(f"Graph {graph_id} not found")
        
        # Create execution context
        context = await context_manager.create_context(initial_state)
        await context.set_status(RunStatus.RUNNING)
        
        if sync:
            # Run synchronously with timeout
            try:
                await asyncio.wait_for(
                    self._execute_workflow(graph, context),
                    timeout=30.0  # 30 second timeout for sync execution
                )
            except asyncio.TimeoutError:
                await context.set_status(RunStatus.TIMEOUT, "Synchronous execution timed out")
        else:
            # Run asynchronously
            asyncio.create_task(self._execute_workflow(graph, context))
        
        # Return result
        return RunResult(
            run_id=context.run_id,
            status=context.status,
            final_state=context.state if sync and context.status == RunStatus.COMPLETED else None,
            logs=context.logs if sync else [],
            created_at=context.created_at,
            completed_at=context.completed_at,
            error_message=context.error_message
        )
    
    async def _execute_workflow(self, graph: Graph, context: ExecutionContext):
        """Execute workflow logic.
        
        Args:
            graph: Graph to execute
            context: Execution context
        """
        try:
            await context.log("engine", f"Starting workflow execution for graph {graph.graph_id}")
            
            # Start with the start node
            current_nodes = [graph.definition.start_node]
            executed_nodes = set()
            
            while current_nodes and context.state.iteration_count < context.state.max_iterations:
                await context.increment_iteration()
                await context.log("engine", f"Starting iteration {context.state.iteration_count}")
                
                next_nodes = []
                
                for node_id in current_nodes:
                    if node_id in executed_nodes:
                        continue  # Skip already executed nodes in this iteration
                    
                    node = graph.nodes.get(node_id)
                    if not node:
                        await context.log("engine", f"Node {node_id} not found", "ERROR")
                        continue
                    
                    await context.set_current_node(node_id)
                    await context.log(node_id, f"Executing node {node_id}")
                    
                    # Execute node
                    result = await node.execute_with_timeout(context)
                    
                    if not result.success:
                        await context.set_status(RunStatus.ERROR, result.error_message)
                        return
                    
                    executed_nodes.add(node_id)
                    
                    # Get next nodes
                    if result.next_nodes:
                        next_nodes.extend(result.next_nodes)
                    else:
                        next_nodes.extend(graph.get_next_nodes(node_id, context))
                
                # Check termination conditions
                if context.state.quality_score >= context.state.quality_threshold:
                    await context.log("engine", 
                        f"Quality threshold reached: {context.state.quality_score} >= {context.state.quality_threshold}")
                    break
                
                # Remove duplicates and continue
                current_nodes = list(set(next_nodes))
                
                if not current_nodes:
                    await context.log("engine", "No more nodes to execute")
                    break
            
            if context.state.iteration_count >= context.state.max_iterations:
                await context.log("engine", 
                    f"Maximum iterations reached: {context.state.max_iterations}", "WARNING")
            
            await context.set_current_node(None)
            await context.set_status(RunStatus.COMPLETED)
            await context.log("engine", "Workflow execution completed successfully")
            
        except Exception as e:
            error_msg = f"Workflow execution failed: {str(e)}"
            await context.set_status(RunStatus.ERROR, error_msg)
            await context.log("engine", error_msg, "ERROR")
    
    async def get_run_status(self, run_id: str) -> Optional[Dict]:
        """Get run status by run ID.
        
        Args:
            run_id: Run identifier
            
        Returns:
            Run status dictionary or None if not found
        """
        context = await context_manager.get_context(run_id)
        if not context:
            return None
        
        return context.to_dict()
    
    async def list_graphs(self) -> List[str]:
        """List all graph IDs.
        
        Returns:
            List of graph IDs
        """
        async with self._lock:
            return list(self._graphs.keys())


# Global graph engine instance
graph_engine = GraphEngine()