"""FastAPI main application for Code Review Mini-Agent."""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from .engine import graph_engine
from .models import (
    GraphCreateRequest, GraphCreateResponse, RunRequest, RunResult,
    RunStatusResponse, ErrorResponse, ExecutionState, RunStatus
)
from .storage import graph_store, run_store
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from workflows import register_code_review_nodes


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Code Review Mini-Agent")
    
    # Register workflow nodes
    register_code_review_nodes()
    logger.info("Registered code review workflow nodes")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Code Review Mini-Agent")


# Create FastAPI app
app = FastAPI(
    title="Code Review Mini-Agent",
    description="A graph-based workflow engine for automated code review",
    version="1.0.0",
    lifespan=lifespan
)


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="internal_server_error",
            message="An internal server error occurred"
        ).dict()
    )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "Code Review Mini-Agent",
        "version": "1.0.0",
        "description": "A graph-based workflow engine for automated code review",
        "endpoints": {
            "create_graph": "POST /graph/create",
            "run_graph": "POST /graph/run",
            "get_run_status": "GET /graph/state/{run_id}"
        }
    }


@app.post("/graph/create", response_model=GraphCreateResponse)
async def create_graph(request: GraphCreateRequest):
    """Create a new workflow graph.
    
    Args:
        request: Graph creation request
        
    Returns:
        Graph creation response with unique graph ID
        
    Raises:
        HTTPException: If graph definition is invalid
    """
    try:
        logger.info(f"Creating graph with {len(request.definition.nodes)} nodes")
        
        # Create graph using engine
        graph_id = await graph_engine.create_graph(request.definition)
        
        # Store in graph store
        await graph_store.create_graph(request.definition)
        
        logger.info(f"Successfully created graph {graph_id}")
        
        return GraphCreateResponse(
            graph_id=graph_id,
            message="Graph created successfully"
        )
        
    except ValueError as e:
        logger.error(f"Graph validation failed: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error="validation_error",
                message=str(e)
            ).dict()
        )
    except Exception as e:
        logger.error(f"Failed to create graph: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="creation_failed",
                message="Failed to create graph"
            ).dict()
        )


@app.post("/graph/run", response_model=RunResult)
async def run_graph(request: RunRequest, sync: bool = Query(False, description="Run synchronously")):
    """Start execution of a workflow graph.
    
    Args:
        request: Run request with graph ID and initial state
        sync: Whether to run synchronously (default: False)
        
    Returns:
        Run result with run ID and status
        
    Raises:
        HTTPException: If graph not found or execution fails
    """
    try:
        logger.info(f"Starting execution of graph {request.graph_id} (sync={sync})")
        
        # Check if graph exists
        graph = await graph_engine.get_graph(request.graph_id)
        if not graph:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="graph_not_found",
                    message=f"Graph {request.graph_id} not found"
                ).dict()
            )
        
        # Execute graph
        result = await graph_engine.execute_graph(
            request.graph_id,
            request.initial_state,
            sync=sync
        )
        
        logger.info(f"Started execution with run ID {result.run_id}")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to start graph execution: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="execution_failed",
                message="Failed to start graph execution"
            ).dict()
        )


@app.get("/graph/state/{run_id}", response_model=RunStatusResponse)
async def get_run_status(run_id: str):
    """Get the current status of a workflow run.
    
    Args:
        run_id: Run identifier
        
    Returns:
        Current run status and state
        
    Raises:
        HTTPException: If run not found
    """
    try:
        logger.debug(f"Getting status for run {run_id}")
        
        # Get run status from engine
        status_data = await graph_engine.get_run_status(run_id)
        if not status_data:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="run_not_found",
                    message=f"Run {run_id} not found"
                ).dict()
            )
        
        # Convert to response model
        from datetime import datetime
        
        response = RunStatusResponse(
            run_id=status_data['run_id'],
            status=RunStatus(status_data['status']),
            current_node=status_data.get('current_node'),
            iteration_count=status_data.get('iteration_count', 0),
            state=ExecutionState(**status_data['state']),
            logs=[],  # Logs are included in the status_data but we'll parse them
            created_at=datetime.fromisoformat(status_data['created_at']),
            completed_at=datetime.fromisoformat(status_data['completed_at']) if status_data.get('completed_at') else None,
            error_message=status_data.get('error_message')
        )
        
        # Parse logs
        for log_data in status_data.get('logs', []):
            from .models import LogEntry
            log_entry = LogEntry(
                timestamp=datetime.fromisoformat(log_data['timestamp']),
                node_id=log_data['node_id'],
                level=log_data['level'],
                message=log_data['message'],
                data=log_data.get('data')
            )
            response.logs.append(log_entry)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get run status: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="status_retrieval_failed",
                message="Failed to retrieve run status"
            ).dict()
        )


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z"
    }


@app.get("/graphs")
async def list_graphs():
    """List all available graphs."""
    try:
        graphs = await graph_engine.list_graphs()
        return {
            "graphs": graphs,
            "count": len(graphs)
        }
    except Exception as e:
        logger.error(f"Failed to list graphs: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="listing_failed",
                message="Failed to list graphs"
            ).dict()
        )


@app.get("/tools")
async def list_tools():
    """List all available tools in the tool registry."""
    try:
        from workflows import list_tools
        tools = list_tools()
        
        # Enhanced tool information
        tool_categories = {
            "extraction": ["parse_code", "count_lines"],
            "complexity": ["calculate_complexity_score"],
            "quality": ["calculate_quality_score"],
            "detection": ["detect_smells"],
            "suggestions": ["generate_suggestions"]
        }
        
        return {
            "tools": tools,
            "count": len(tools),
            "categories": tool_categories,
            "description": "Modular analysis tools for code review workflow"
        }
    except Exception as e:
        logger.error(f"Failed to list tools: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="listing_failed",
                message="Failed to list tools"
            ).dict()
        )


if __name__ == "__main__":
    import uvicorn
    import os
    
    # Get port from environment variable or use default
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    
    uvicorn.run(app, host=host, port=port)