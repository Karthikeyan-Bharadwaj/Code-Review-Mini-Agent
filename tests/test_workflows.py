"""
Tests for workflow nodes.

These tests verify the workflow node execution and state management.
"""

import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import ExecutionState, CodeIssue, IssueType, IssueSeverity
from workflows import ExtractNode, ComplexityNode, IssuesNode, SuggestNode
from registry import NodeResult


class TestWorkflowNodes:
    """Test suite for workflow nodes."""
    
    @pytest.fixture
    def mock_context(self):
        """Create mock execution context."""
        context = AsyncMock()
        context.state = ExecutionState(
            source_code="def test_function():\n    return True",
            quality_threshold=80.0,
            max_iterations=10
        )
        context.log = AsyncMock()
        context.update_state = AsyncMock()
        return context
    
    @pytest.mark.asyncio
    async def test_extract_node_success(self, mock_context):
        """Test successful extraction node execution."""
        node = ExtractNode("extract", {})
        
        result = await node.execute(mock_context)
        
        # Verify successful execution
        assert isinstance(result, NodeResult)
        assert result.success is True
        assert result.error_message is None
        
        # Verify state was updated
        mock_context.update_state.assert_called_once()
        
        # Verify logging occurred
        assert mock_context.log.call_count >= 2  # Start and completion logs
    
    @pytest.mark.asyncio
    async def test_extract_node_empty_code(self, mock_context):
        """Test extraction node with empty source code."""
        mock_context.state.source_code = ""
        
        node = ExtractNode("extract", {})
        result = await node.execute(mock_context)
        
        # Should still succeed but log warning
        assert result.success is True
        
        # Should log warning about empty code
        warning_logged = any(
            call.args[2] == "WARNING" 
            for call in mock_context.log.call_args_list
        )
        assert warning_logged
    
    @pytest.mark.asyncio
    async def test_complexity_node_success(self, mock_context):
        """Test successful complexity node execution."""
        # Set up state with extracted metrics
        mock_context.state.lines_of_code = 5
        mock_context.state.nested_blocks = 1
        mock_context.state.long_names = []
        
        node = ComplexityNode("complexity", {})
        result = await node.execute(mock_context)
        
        # Verify successful execution
        assert result.success is True
        
        # Verify state update was called
        mock_context.update_state.assert_called_once()
        update_args = mock_context.update_state.call_args[0][0]
        assert 'complexity_score' in update_args
        assert isinstance(update_args['complexity_score'], float)
    
    @pytest.mark.asyncio
    async def test_issues_node_success(self, mock_context):
        """Test successful issues node execution."""
        # Set up state with metrics
        mock_context.state.lines_of_code = 10
        mock_context.state.nested_blocks = 2
        mock_context.state.long_names = []
        mock_context.state.cyclomatic_complexity = 3
        mock_context.state.functions_found = 1
        mock_context.state.todo_comments = []
        mock_context.state.print_statements = []
        mock_context.state.bare_exceptions = []
        
        node = IssuesNode("issues", {})
        result = await node.execute(mock_context)
        
        # Verify successful execution
        assert result.success is True
        
        # Verify state update was called
        mock_context.update_state.assert_called_once()
        update_args = mock_context.update_state.call_args[0][0]
        assert 'issues' in update_args
        assert isinstance(update_args['issues'], list)
    
    @pytest.mark.asyncio
    async def test_suggest_node_success(self, mock_context):
        """Test successful suggest node execution."""
        # Set up state with previous analysis results
        mock_context.state.complexity_score = 75.0
        mock_context.state.issues = [
            CodeIssue(
                type=IssueType.STYLE,
                severity=IssueSeverity.LOW,
                description="Test issue",
                suggestion="Test suggestion"
            )
        ]
        mock_context.state.lines_of_code = 10
        mock_context.state.nested_blocks = 1
        mock_context.state.functions_found = 1
        mock_context.state.cyclomatic_complexity = 2
        
        node = SuggestNode("suggest", {})
        result = await node.execute(mock_context)
        
        # Verify successful execution
        assert result.success is True
        
        # Verify state update was called
        mock_context.update_state.assert_called_once()
        update_args = mock_context.update_state.call_args[0][0]
        assert 'quality_score' in update_args
        assert 'suggestions' in update_args
        assert isinstance(update_args['quality_score'], float)
        assert isinstance(update_args['suggestions'], list)
    
    @pytest.mark.asyncio
    async def test_node_error_handling(self, mock_context):
        """Test node error handling when tools fail."""
        # Make update_state raise an exception
        mock_context.update_state.side_effect = Exception("Test error")
        
        node = ExtractNode("extract", {})
        result = await node.execute(mock_context)
        
        # Should handle error gracefully
        assert result.success is False
        assert result.error_message is not None
        assert "Test error" in result.error_message
        
        # Should log error
        error_logged = any(
            call.args[2] == "ERROR" 
            for call in mock_context.log.call_args_list
        )
        assert error_logged


class TestNodeIntegration:
    """Integration tests for node workflow."""
    
    @pytest.fixture
    def execution_state(self):
        """Create execution state for testing."""
        return ExecutionState(
            source_code="""def calculate_average(numbers):
    # TODO: Add input validation
    total = 0
    count = 0
    for num in numbers:
        if num > 0:
            total += num
            count += 1
    print(f"Processing {count} numbers")
    return total / count if count > 0 else 0""",
            quality_threshold=80.0,
            max_iterations=10
        )
    
    @pytest.mark.asyncio
    async def test_complete_node_workflow(self, execution_state):
        """Test complete workflow through all nodes."""
        # Create mock context
        context = AsyncMock()
        context.state = execution_state
        context.log = AsyncMock()
        
        # Track state updates
        state_updates = {}
        
        def update_state_side_effect(updates):
            state_updates.update(updates)
            for key, value in updates.items():
                setattr(context.state, key, value)
        
        context.update_state.side_effect = update_state_side_effect
        
        # Execute nodes in sequence
        nodes = [
            ExtractNode("extract", {}),
            ComplexityNode("complexity", {}),
            IssuesNode("issues", {}),
            SuggestNode("suggest", {})
        ]
        
        for node in nodes:
            result = await node.execute(context)
            assert result.success is True, f"Node {node.node_id} failed: {result.error_message}"
        
        # Verify final state has all expected fields
        expected_fields = [
            'lines_of_code', 'functions_found', 'complexity_score',
            'quality_score', 'issues', 'suggestions'
        ]
        
        for field in expected_fields:
            assert hasattr(context.state, field), f"Missing field: {field}"
        
        # Verify reasonable values
        assert context.state.lines_of_code > 0
        assert context.state.functions_found == 1
        assert 0 <= context.state.complexity_score <= 100
        assert context.state.quality_score >= 0
        assert isinstance(context.state.issues, list)
        assert isinstance(context.state.suggestions, list)
        assert len(context.state.suggestions) > 0


if __name__ == "__main__":
    pytest.main([__file__])