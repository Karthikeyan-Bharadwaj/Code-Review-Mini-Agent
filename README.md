# Code Review Mini-Agent

A lightweight, graph-based workflow engine built with FastAPI that performs deterministic Python code analysis. It evaluates code complexity, detects common issues, and generates actionable suggestions using a rule-based workflow.

## Overview / Description

The Code Review Mini-Agent analyzes Python code step by step using a deterministic workflow. It extracts functions, computes complexity, identifies issues, and iterates until a quality target is met. This project demonstrates backend workflow orchestration, state management, and clean API design using FastAPI.

**What it does:**
- Extracts and analyzes Python functions
- Computes complexity based on line count and nesting
- Detects issues such as long lines, high complexity, and poor naming
- Generates practical suggestions for improvement
- Computes a 0–100 quality score
- Loops until the required quality threshold is reached

## Installation

### Requirements
- Python 3.8+
- pip installed

### Steps
```bash
# Download or clone the project files to your local machine
cd code-review-mini-agent
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## How to Run

**Start the server:**
```bash
uvicorn app.main:app --reload
```

**Access the API:**
- Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

**Run tests:**
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_tools.py -v
```

## Features

- **Graph-based workflow execution**
- **Rule-based Code Review Mini-Agent**
- **Deterministic results** (same code -> same output)
- **Async support** for long-running analysis
- **Shared state** and step-by-step logging
- **Extensible tool** & workflow registration
- **Clean JSON outputs** and easy REST integration
- **Comprehensive test suite** with unit, integration, and API tests

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/graph/create` | Create a new graph/workflow |
| POST | `/graph/run` | Run the analysis (sync/async) |
| GET | `/graph/state/{run_id}` | Get current or final analysis state |
| GET | `/health` | API health status |

## Example Usage

### 1. Create Workflow
```bash
curl -X POST "http://localhost:8000/graph/create" \
  -H "Content-Type: application/json" \
  -d '{
    "definition": {
      "nodes": {
        "extract": {"id": "extract", "type": "extract", "config": {}},
        "complexity": {"id": "complexity", "type": "complexity", "config": {}},
        "issues": {"id": "issues", "type": "issues", "config": {}},
        "suggest": {"id": "suggest", "type": "suggest", "config": {}}
      },
      "edges": [
        {"from_node": "extract", "to_node": "complexity"},
        {"from_node": "complexity", "to_node": "issues"},
        {"from_node": "issues", "to_node": "suggest"},
        {"from_node": "suggest", "to_node": "complexity", "condition": "state.quality_score < 80"}
      ],
      "start_node": "extract"
    }
  }'
```

### 2. Run Analysis
```bash
curl -X POST "http://localhost:8000/graph/run?sync=true" \
  -H "Content-Type: application/json" \
  -d '{
    "graph_id": "your-graph-id",
    "initial_state": {
      "source_code": "def sample(x): return x*2",
      "quality_threshold": 80,
      "max_iterations": 10
    }
  }'
```

## Example Input & Output

### Input Code
```python
def example(data):
    result = []
    for i in range(len(data)):
        if data[i] > 0:
            for j in range(data[i]):
                result.append(j)
    return result
```

### Output (Simplified)
```json
{
  "status": "completed",
  "final_state": {
    "complexity_score": 72.0,
    "quality_score": 52.0,
    "lines_of_code": 6,
    "nested_blocks": 2,
    "functions_found": 1,
    "cyclomatic_complexity": 3,
    "issues": [
      {
        "type": "structure",
        "severity": "medium", 
        "description": "Too many nested blocks (2)",
        "suggestion": "Reduce nesting by using early returns or extracting methods"
      },
      {
        "type": "complexity",
        "severity": "medium",
        "description": "High cyclomatic complexity (3)",
        "suggestion": "Reduce complexity by extracting methods or simplifying logic"
      }
    ],
    "suggestions": [
      "Code quality is fair - addressing identified issues will improve maintainability",
      "Reduce cyclomatic complexity by extracting methods or simplifying conditional logic",
      "Improve code structure by reducing nesting and using early returns"
    ],
    "iteration_count": 1
  }
}
```

**Quality Rating:**
- **80-100**: Excellent
- **60-79**: Good  
- **40-59**: Fair (like this example: 52.0)
- **20-39**: Poor
- **0-19**: Very Poor
```

## Project Structure

```
code-review-mini-agent/
├── app/
│   ├── main.py              # FastAPI application and routes
│   ├── engine.py            # Graph execution engine
│   ├── models.py            # Pydantic data models
│   └── storage.py           # In-memory data storage
├── tests/                   # Comprehensive test suite
│   ├── __init__.py          # Test package with utilities and fixtures
│   ├── test_tools.py        # Tests for analysis tools
│   ├── test_api.py          # Tests for FastAPI endpoints
│   └── test_workflows.py    # Tests for workflow nodes
├── workflows.py             # Clean workflow node implementations
├── tools.py                 # Modular analysis tools and helper functions
├── registry.py              # Node registry and base classes
├── requirements.txt         # Python dependencies
├── README.md                # Project documentation
├── LICENSE                  # MIT License
└── .gitignore               # Git ignore rules
```

## Testing

The project includes a comprehensive test suite demonstrating backend maturity and reliability:

### Test Categories
- **Unit Tests** (`test_tools.py`): Core analysis functions and edge cases
- **API Tests** (`test_api.py`): FastAPI endpoint functionality and error handling  
- **Workflow Tests** (`test_workflows.py`): Node execution and integration flows

### Test Coverage
- **Tools Module**: Parsing, complexity calculation, issue detection, scoring
- **API Endpoints**: All REST endpoints with success and error scenarios
- **Workflow Nodes**: Individual node execution and complete workflow integration
- **Edge Cases**: Empty code, invalid syntax, boundary values, error handling

### Running Tests
```bash
# Run all tests with verbose output
pytest -v

# Run with coverage report
pytest --cov=. --cov-report=html

# Run specific test categories
pytest tests/test_tools.py      # Unit tests
pytest tests/test_api.py        # API tests  
pytest tests/test_workflows.py  # Workflow tests
```

## Future Improvements

- **WebSocket live log streaming**
- **Database storage** for graphs and run history
- **More advanced static analysis rules**
- **Support for additional languages**
- **Dashboard UI** for visualizing results

## License

This project is licensed under the **MIT License**. You are free to use, modify, and distribute it with attribution.
