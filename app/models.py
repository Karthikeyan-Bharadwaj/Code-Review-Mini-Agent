"""Pydantic models for API requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel, Field, validator


class NodeType(str, Enum):
    """Types of nodes in the workflow."""
    EXTRACT = "extract"
    COMPLEXITY = "complexity"
    ISSUES = "issues"
    SUGGEST = "suggest"
    CUSTOM = "custom"


class RunStatus(str, Enum):
    """Status of workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"


class IssueSeverity(str, Enum):
    """Severity levels for code issues."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IssueType(str, Enum):
    """Types of code issues."""
    COMPLEXITY = "complexity"
    NAMING = "naming"
    STRUCTURE = "structure"
    STYLE = "style"


class EdgeDefinition(BaseModel):
    """Definition of an edge between nodes."""
    from_node: str = Field(..., description="Source node ID")
    to_node: str = Field(..., description="Target node ID")
    condition: Optional[str] = Field(None, description="Condition for edge traversal")


class NodeDefinition(BaseModel):
    """Definition of a workflow node."""
    id: str = Field(..., description="Unique node identifier")
    type: NodeType = Field(..., description="Type of node")
    config: Dict[str, Any] = Field(default_factory=dict, description="Node configuration")


class GraphDefinition(BaseModel):
    """Definition of a complete workflow graph."""
    nodes: Dict[str, NodeDefinition] = Field(..., description="Map of node ID to node definition")
    edges: List[EdgeDefinition] = Field(..., description="List of edges between nodes")
    start_node: str = Field(..., description="ID of the starting node")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Graph metadata")

    @validator('start_node')
    def validate_start_node(cls, v, values):
        """Validate that start_node exists in nodes."""
        if 'nodes' in values and v not in values['nodes']:
            raise ValueError(f"Start node '{v}' not found in nodes")
        return v


class CodeIssue(BaseModel):
    """Represents a code quality issue."""
    type: IssueType = Field(..., description="Type of issue")
    severity: IssueSeverity = Field(..., description="Severity level")
    line_number: Optional[int] = Field(None, description="Line number where issue occurs")
    description: str = Field(..., description="Description of the issue")
    suggestion: str = Field(..., description="Suggested fix for the issue")


class ExecutionState(BaseModel):
    """State maintained during workflow execution."""
    # Input data
    source_code: str = Field(default="", description="Source code being analyzed")
    
    # Extracted metrics
    lines_of_code: int = Field(default=0, description="Number of lines of code")
    nested_blocks: int = Field(default=0, description="Number of nested blocks")
    long_names: List[str] = Field(default_factory=list, description="List of long variable/function names")
    
    # Calculated scores
    complexity_score: float = Field(default=0.0, description="Complexity score (0-100)")
    quality_score: float = Field(default=0.0, description="Quality score (0-100)")
    
    # Issues and suggestions
    issues: List[CodeIssue] = Field(default_factory=list, description="Identified code issues")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")
    
    # Loop control
    iteration_count: int = Field(default=0, description="Current iteration number")
    quality_threshold: float = Field(default=80.0, description="Quality threshold for loop termination")
    max_iterations: int = Field(default=10, description="Maximum number of iterations")
    
    # Additional state
    custom_data: Dict[str, Any] = Field(default_factory=dict, description="Custom state data")


class LogEntry(BaseModel):
    """A single log entry from workflow execution."""
    timestamp: datetime = Field(default_factory=datetime.now, description="When the log entry was created")
    node_id: str = Field(..., description="ID of the node that generated this log")
    level: str = Field(default="INFO", description="Log level (INFO, WARNING, ERROR)")
    message: str = Field(..., description="Log message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Additional log data")


class RunRequest(BaseModel):
    """Request to start a workflow run."""
    graph_id: str = Field(..., description="ID of the graph to execute")
    initial_state: ExecutionState = Field(..., description="Initial state for execution")
    sync: bool = Field(default=False, description="Whether to run synchronously")


class RunResult(BaseModel):
    """Result of a workflow run."""
    run_id: str = Field(..., description="Unique run identifier")
    status: RunStatus = Field(..., description="Current run status")
    final_state: Optional[ExecutionState] = Field(None, description="Final execution state")
    logs: List[LogEntry] = Field(default_factory=list, description="Execution logs")
    created_at: datetime = Field(default_factory=datetime.now, description="When the run was created")
    completed_at: Optional[datetime] = Field(None, description="When the run completed")
    error_message: Optional[str] = Field(None, description="Error message if run failed")


class GraphCreateRequest(BaseModel):
    """Request to create a new graph."""
    definition: GraphDefinition = Field(..., description="Graph definition")


class GraphCreateResponse(BaseModel):
    """Response from graph creation."""
    graph_id: str = Field(..., description="Unique identifier for the created graph")
    message: str = Field(default="Graph created successfully", description="Success message")


class RunStatusResponse(BaseModel):
    """Response for run status queries."""
    run_id: str = Field(..., description="Run identifier")
    status: RunStatus = Field(..., description="Current run status")
    current_node: Optional[str] = Field(None, description="Currently executing node")
    iteration_count: int = Field(default=0, description="Current iteration count")
    state: ExecutionState = Field(..., description="Current execution state")
    logs: List[LogEntry] = Field(default_factory=list, description="Execution logs")
    created_at: datetime = Field(..., description="When the run was created")
    completed_at: Optional[datetime] = Field(None, description="When the run completed")
    error_message: Optional[str] = Field(None, description="Error message if run failed")


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")