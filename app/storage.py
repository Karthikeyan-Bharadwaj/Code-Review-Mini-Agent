"""In-memory storage for graphs and execution runs."""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from .models import GraphDefinition, ExecutionState, RunStatus


class GraphStore:
    """In-memory storage for graph definitions."""
    
    def __init__(self):
        """Initialize graph store."""
        self._graphs: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def create_graph(self, definition: GraphDefinition) -> str:
        """Store a graph definition and return unique ID.
        
        Args:
            definition: Graph definition to store
            
        Returns:
            Unique graph ID
        """
        graph_id = str(uuid4())
        
        async with self._lock:
            self._graphs[graph_id] = {
                'id': graph_id,
                'definition': definition.dict(),
                'created_at': datetime.now().isoformat(),
                'metadata': definition.metadata or {}
            }
        
        return graph_id
    
    async def get_graph(self, graph_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve graph by ID.
        
        Args:
            graph_id: Graph identifier
            
        Returns:
            Graph data or None if not found
        """
        async with self._lock:
            return self._graphs.get(graph_id)
    
    async def list_graphs(self) -> List[Dict[str, Any]]:
        """List all stored graphs.
        
        Returns:
            List of graph data
        """
        async with self._lock:
            return list(self._graphs.values())
    
    async def delete_graph(self, graph_id: str) -> bool:
        """Delete a graph.
        
        Args:
            graph_id: Graph identifier
            
        Returns:
            True if graph was deleted, False if not found
        """
        async with self._lock:
            return self._graphs.pop(graph_id, None) is not None
    
    async def graph_exists(self, graph_id: str) -> bool:
        """Check if graph exists.
        
        Args:
            graph_id: Graph identifier
            
        Returns:
            True if graph exists
        """
        async with self._lock:
            return graph_id in self._graphs


class RunStore:
    """In-memory storage for execution runs."""
    
    def __init__(self):
        """Initialize run store."""
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def create_run(self, graph_id: str, initial_state: ExecutionState) -> str:
        """Create a new run record.
        
        Args:
            graph_id: ID of the graph being executed
            initial_state: Initial execution state
            
        Returns:
            Unique run ID
        """
        run_id = str(uuid4())
        
        async with self._lock:
            self._runs[run_id] = {
                'run_id': run_id,
                'graph_id': graph_id,
                'status': RunStatus.PENDING.value,
                'initial_state': initial_state.dict(),
                'current_state': initial_state.dict(),
                'current_node': None,
                'iteration_count': 0,
                'logs': [],
                'created_at': datetime.now().isoformat(),
                'completed_at': None,
                'error_message': None
            }
        
        return run_id
    
    async def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve run by ID.
        
        Args:
            run_id: Run identifier
            
        Returns:
            Run data or None if not found
        """
        async with self._lock:
            return self._runs.get(run_id)
    
    async def update_run(self, run_id: str, updates: Dict[str, Any]) -> bool:
        """Update run data.
        
        Args:
            run_id: Run identifier
            updates: Dictionary of updates to apply
            
        Returns:
            True if run was updated, False if not found
        """
        async with self._lock:
            if run_id not in self._runs:
                return False
            
            self._runs[run_id].update(updates)
            return True
    
    async def update_run_status(self, run_id: str, status: RunStatus, 
                              error_message: Optional[str] = None) -> bool:
        """Update run status.
        
        Args:
            run_id: Run identifier
            status: New run status
            error_message: Error message if status is ERROR
            
        Returns:
            True if run was updated, False if not found
        """
        updates = {'status': status.value}
        
        if error_message:
            updates['error_message'] = error_message
        
        if status in [RunStatus.COMPLETED, RunStatus.ERROR, RunStatus.TIMEOUT]:
            updates['completed_at'] = datetime.now().isoformat()
        
        return await self.update_run(run_id, updates)
    
    async def update_run_state(self, run_id: str, state: ExecutionState) -> bool:
        """Update run execution state.
        
        Args:
            run_id: Run identifier
            state: New execution state
            
        Returns:
            True if run was updated, False if not found
        """
        updates = {
            'current_state': state.dict(),
            'iteration_count': state.iteration_count
        }
        
        return await self.update_run(run_id, updates)
    
    async def add_run_log(self, run_id: str, log_entry: Dict[str, Any]) -> bool:
        """Add a log entry to a run.
        
        Args:
            run_id: Run identifier
            log_entry: Log entry data
            
        Returns:
            True if log was added, False if run not found
        """
        async with self._lock:
            if run_id not in self._runs:
                return False
            
            self._runs[run_id]['logs'].append(log_entry)
            return True
    
    async def set_current_node(self, run_id: str, node_id: Optional[str]) -> bool:
        """Set the currently executing node for a run.
        
        Args:
            run_id: Run identifier
            node_id: Current node ID or None
            
        Returns:
            True if run was updated, False if not found
        """
        return await self.update_run(run_id, {'current_node': node_id})
    
    async def list_runs(self, graph_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List runs, optionally filtered by graph ID.
        
        Args:
            graph_id: Optional graph ID to filter by
            
        Returns:
            List of run data
        """
        async with self._lock:
            runs = list(self._runs.values())
            
            if graph_id:
                runs = [run for run in runs if run['graph_id'] == graph_id]
            
            return runs
    
    async def delete_run(self, run_id: str) -> bool:
        """Delete a run.
        
        Args:
            run_id: Run identifier
            
        Returns:
            True if run was deleted, False if not found
        """
        async with self._lock:
            return self._runs.pop(run_id, None) is not None
    
    async def run_exists(self, run_id: str) -> bool:
        """Check if run exists.
        
        Args:
            run_id: Run identifier
            
        Returns:
            True if run exists
        """
        async with self._lock:
            return run_id in self._runs
    
    async def cleanup_completed_runs(self, max_age_hours: int = 24) -> int:
        """Clean up old completed runs.
        
        Args:
            max_age_hours: Maximum age in hours for completed runs
            
        Returns:
            Number of runs cleaned up
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        cleaned_count = 0
        
        async with self._lock:
            runs_to_delete = []
            
            for run_id, run_data in self._runs.items():
                if run_data['status'] in [RunStatus.COMPLETED.value, RunStatus.ERROR.value, RunStatus.TIMEOUT.value]:
                    if run_data['completed_at']:
                        completed_at = datetime.fromisoformat(run_data['completed_at'])
                        if completed_at < cutoff_time:
                            runs_to_delete.append(run_id)
            
            for run_id in runs_to_delete:
                del self._runs[run_id]
                cleaned_count += 1
        
        return cleaned_count


# Global storage instances
graph_store = GraphStore()
run_store = RunStore()