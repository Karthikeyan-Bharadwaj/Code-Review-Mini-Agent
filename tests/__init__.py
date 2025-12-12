"""
Test Suite for Code Review Mini-Agent

This package contains comprehensive tests for the Code Review Mini-Agent project,
demonstrating backend maturity and reliability through thorough testing practices.

Test Categories:
- Unit Tests: Core analysis functions and algorithms
- API Tests: FastAPI endpoint functionality and error handling
- Workflow Tests: Node execution and integration flows
- Integration Tests: End-to-end workflow validation

Test Coverage:
- Tools module: Parsing, complexity calculation, issue detection
- API endpoints: All REST endpoints with success/error scenarios  
- Workflow nodes: Individual and integrated node execution
- Edge cases: Error handling, boundary values, invalid inputs

Usage:
    pytest                    # Run all tests
    pytest -v                # Verbose output
    pytest --cov=.           # With coverage
    pytest tests/test_tools.py  # Specific test file
"""

__version__ = "1.0.0"
__author__ = "Code Review Mini-Agent Team"

# Test configuration
TEST_TIMEOUT = 30  # seconds
DEFAULT_QUALITY_THRESHOLD = 80.0
MAX_TEST_ITERATIONS = 5

# Sample test data
SAMPLE_SIMPLE_CODE = """def hello_world():
    print("Hello, World!")
    return True"""

SAMPLE_COMPLEX_CODE = """def complex_function(data):
    # TODO: Optimize this function
    result = []
    try:
        for i in range(len(data)):
            if data[i] > 0:
                for j in range(data[i]):
                    result.append(j)
        print(f"Processed {len(result)} items")
    except:
        pass
    return result"""

# Test utilities
def get_test_graph_definition():
    """Get a standard test graph definition."""
    return {
        "nodes": {
            "extract": {"id": "extract", "type": "extract", "config": {}},
            "complexity": {"id": "complexity", "type": "complexity", "config": {}},
            "issues": {"id": "issues", "type": "issues", "config": {}},
            "suggest": {"id": "suggest", "type": "suggest", "config": {}}
        },
        "edges": [
            {"from_node": "extract", "to_node": "complexity"},
            {"from_node": "complexity", "to_node": "issues"},
            {"from_node": "issues", "to_node": "suggest"}
        ],
        "start_node": "extract"
    }

def get_test_execution_state(source_code=None):
    """Get a standard test execution state."""
    return {
        "source_code": source_code or SAMPLE_SIMPLE_CODE,
        "quality_threshold": DEFAULT_QUALITY_THRESHOLD,
        "max_iterations": MAX_TEST_ITERATIONS
    }