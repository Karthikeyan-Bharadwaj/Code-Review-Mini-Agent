"""
Tests for FastAPI endpoints.

These tests verify the API functionality and ensure proper request/response handling.
"""

import pytest
import sys
import os

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.main import app


class TestAPIEndpoints:
    """Test suite for API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns API information."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected fields
        assert "name" in data
        assert "version" in data
        assert "description" in data
        assert "endpoints" in data
        
        # Verify values
        assert data["name"] == "Code Review Mini-Agent"
        assert data["version"] == "1.0.0"
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "status" in data
        assert data["status"] == "healthy"
        assert "timestamp" in data
    
    def test_tools_endpoint(self, client):
        """Test tools listing endpoint."""
        response = client.get("/tools")
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify expected structure
        assert "tools" in data
        assert "count" in data
        assert "categories" in data
        assert "description" in data
        
        # Verify tools are listed
        assert isinstance(data["tools"], list)
        assert data["count"] == len(data["tools"])
        assert data["count"] > 0
        
        # Verify categories structure
        categories = data["categories"]
        expected_categories = ["extraction", "complexity", "quality", "detection", "suggestions"]
        for category in expected_categories:
            assert category in categories
    
    def test_create_graph_endpoint(self, client):
        """Test graph creation endpoint."""
        from tests import get_test_graph_definition
        
        graph_definition = {
            "definition": get_test_graph_definition()
        }
        
        response = client.post("/graph/create", json=graph_definition)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "graph_id" in data
        assert "message" in data
        
        # Verify graph_id is a valid UUID-like string
        graph_id = data["graph_id"]
        assert isinstance(graph_id, str)
        assert len(graph_id) > 0
    
    def test_create_graph_invalid_definition(self, client):
        """Test graph creation with invalid definition."""
        invalid_definition = {
            "definition": {
                "nodes": {},  # Empty nodes
                "edges": [],
                "start_node": "nonexistent"  # Start node doesn't exist
            }
        }
        
        response = client.post("/graph/create", json=invalid_definition)
        
        # Should return validation error
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
    
    def test_run_graph_nonexistent(self, client):
        """Test running a non-existent graph."""
        run_request = {
            "graph_id": "nonexistent-graph-id",
            "initial_state": {
                "source_code": "def test(): pass",
                "quality_threshold": 80,
                "max_iterations": 10
            }
        }
        
        response = client.post("/graph/run", json=run_request)
        
        # Should return not found error
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
    
    def test_get_run_status_nonexistent(self, client):
        """Test getting status of non-existent run."""
        response = client.get("/graph/state/nonexistent-run-id")
        
        # Should return not found error
        assert response.status_code == 404
        data = response.json()
        assert "error" in data


class TestIntegrationWorkflow:
    """Integration tests for complete workflow."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    def test_complete_workflow_integration(self, client):
        """Test complete workflow from graph creation to execution."""
        from tests import get_test_graph_definition, get_test_execution_state
        
        # Step 1: Create a graph
        graph_definition = {
            "definition": get_test_graph_definition()
        }
        
        create_response = client.post("/graph/create", json=graph_definition)
        assert create_response.status_code == 200
        
        graph_id = create_response.json()["graph_id"]
        
        # Step 2: Run the graph synchronously
        run_request = {
            "graph_id": graph_id,
            "initial_state": get_test_execution_state("def simple_function(x):\n    return x * 2")
        }
        
        run_response = client.post("/graph/run?sync=true", json=run_request)
        assert run_response.status_code == 200
        
        run_data = run_response.json()
        
        # Verify run response structure
        assert "run_id" in run_data
        assert "status" in run_data
        assert "final_state" in run_data
        
        # Step 3: Verify the analysis results
        final_state = run_data["final_state"]
        
        # Should have extracted metrics
        assert "lines_of_code" in final_state
        assert "functions_found" in final_state
        assert final_state["functions_found"] == 1
        
        # Should have calculated scores
        assert "complexity_score" in final_state
        assert "quality_score" in final_state
        
        # Should have generated suggestions
        assert "suggestions" in final_state
        assert isinstance(final_state["suggestions"], list)


if __name__ == "__main__":
    pytest.main([__file__])