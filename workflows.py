"""Code review workflow implementation with clean, modular nodes."""

from typing import List, Dict, Any

from app.models import CodeIssue, IssueType, IssueSeverity
from registry import Node, NodeResult, node_registry

# Import ExecutionContext from engine since we moved it there
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))
from app.engine import ExecutionContext

# Import all tools from the tools module
from tools import (
    # Extraction tools
    parse_python_code,
    count_lines_of_code,
    count_functions,
    count_classes,
    
    # Complexity analysis tools
    count_nested_blocks,
    calculate_cyclomatic_complexity,
    calculate_complexity_score,
    
    # Issue detection tools
    find_long_names,
    detect_todo_comments,
    detect_print_statements,
    detect_bare_exceptions,
    detect_code_smells,
    
    # Quality scoring tools
    calculate_quality_score,
    get_quality_rating,
    
    # Suggestion generation tools
    generate_improvement_suggestions,
    
    # Utility functions
    format_analysis_summary
)


# Tool Registry - Dictionary of available tools that nodes can call
tool_registry = {}

def register_tool(name: str, func):
    """Register a tool function in the tool registry."""
    tool_registry[name] = func
    return func

def get_tool(name: str):
    """Get a tool function from the registry."""
    return tool_registry.get(name)

def list_tools():
    """List all available tools."""
    return list(tool_registry.keys())


# Register all tools from tools.py
@register_tool("parse_code")
def _parse_code_tool(source_code: str) -> Dict[str, Any]:
    """Tool wrapper for parse_python_code."""
    return parse_python_code(source_code)

@register_tool("count_lines")
def _count_lines_tool(source_code: str) -> int:
    """Tool wrapper for count_lines_of_code."""
    return count_lines_of_code(source_code)

@register_tool("calculate_complexity_score")
def _complexity_score_tool(lines_of_code: int, nested_blocks: int, long_names: List[str]) -> float:
    """Tool wrapper for calculate_complexity_score."""
    return calculate_complexity_score(lines_of_code, nested_blocks, long_names)

@register_tool("calculate_quality_score")
def _quality_score_tool(complexity_score: float, num_issues: int) -> float:
    """Tool wrapper for calculate_quality_score."""
    return calculate_quality_score(complexity_score, num_issues)

@register_tool("detect_smells")
def _detect_smells_tool(source_code: str, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Tool wrapper for detect_code_smells."""
    return detect_code_smells(source_code, metrics)

@register_tool("generate_suggestions")
def _generate_suggestions_tool(complexity_score: float, quality_score: float, 
                              issues: List[Dict[str, Any]], metrics: Dict[str, Any]) -> List[str]:
    """Tool wrapper for generate_improvement_suggestions."""
    return generate_improvement_suggestions(complexity_score, quality_score, issues, metrics)


# =============================================================================
# CLEAN WORKFLOW NODES - Using tools for modularity
# =============================================================================

class ExtractNode(Node):
    """Node that extracts comprehensive metrics from source code."""
    
    async def execute(self, context: ExecutionContext) -> NodeResult:
        """Extract code metrics and store in state."""
        try:
            source_code = context.state.source_code
            if not source_code.strip():
                await context.log(self.node_id, "No source code provided", "WARNING")
                return NodeResult(success=True)
            
            await context.log(self.node_id, "Parsing source code and extracting comprehensive metrics")
            
            # Use tools to extract all metrics
            metrics = parse_python_code(source_code)
            
            # Update state with all extracted metrics
            await context.update_state({
                'lines_of_code': metrics['lines_of_code'],
                'nested_blocks': metrics['nested_blocks'],
                'long_names': metrics['long_names'],
                'functions_found': metrics['functions_found'],
                'classes_found': metrics['classes_found'],
                'cyclomatic_complexity': metrics['cyclomatic_complexity'],
                'todo_comments': metrics['todo_comments'],
                'print_statements': metrics['print_statements'],
                'bare_exceptions': metrics['bare_exceptions']
            })
            
            await context.log(self.node_id, 
                f"Extracted metrics: {metrics['lines_of_code']} LOC, "
                f"{metrics['functions_found']} functions, "
                f"{metrics['nested_blocks']} nested blocks, "
                f"{len(metrics['long_names'])} long names")
            
            return NodeResult(success=True)
            
        except Exception as e:
            error_msg = f"Failed to extract code metrics: {str(e)}"
            await context.log(self.node_id, error_msg, "ERROR")
            return NodeResult(success=False, error_message=error_msg)


class ComplexityNode(Node):
    """Node that calculates complexity scores using tools."""
    
    async def execute(self, context: ExecutionContext) -> NodeResult:
        """Calculate complexity score and store in state."""
        try:
            await context.log(self.node_id, "Calculating complexity score")
            
            # Get metrics from state
            lines_of_code = context.state.lines_of_code
            nested_blocks = context.state.nested_blocks
            long_names = context.state.long_names
            
            # Use tool to calculate complexity score
            complexity_score = calculate_complexity_score(lines_of_code, nested_blocks, long_names)
            
            # Update state
            await context.update_state({'complexity_score': complexity_score})
            
            await context.log(self.node_id, f"Calculated complexity score: {complexity_score:.2f}")
            
            return NodeResult(success=True)
            
        except Exception as e:
            error_msg = f"Failed to calculate complexity score: {str(e)}"
            await context.log(self.node_id, error_msg, "ERROR")
            return NodeResult(success=False, error_message=error_msg)


class IssuesNode(Node):
    """Node that identifies code quality issues using comprehensive tools."""
    
    async def execute(self, context: ExecutionContext) -> NodeResult:
        """Identify code issues and store in state."""
        try:
            await context.log(self.node_id, "Analyzing code for quality issues")
            
            source_code = context.state.source_code
            
            # Prepare comprehensive metrics for issue detection
            metrics = {
                'lines_of_code': context.state.lines_of_code,
                'nested_blocks': context.state.nested_blocks,
                'long_names': context.state.long_names,
                'cyclomatic_complexity': context.state.cyclomatic_complexity,
                'functions_found': context.state.functions_found,
                'todo_comments': context.state.todo_comments,
                'print_statements': context.state.print_statements,
                'bare_exceptions': context.state.bare_exceptions
            }
            
            # Use tool to detect code smells and issues
            raw_issues = detect_code_smells(source_code, metrics)
            
            # Convert to CodeIssue objects
            issues = []
            for issue_data in raw_issues:
                issue = CodeIssue(
                    type=IssueType(issue_data['type']),
                    severity=IssueSeverity(issue_data['severity']),
                    line_number=issue_data.get('line_number'),
                    description=issue_data['description'],
                    suggestion=issue_data['suggestion']
                )
                issues.append(issue)
            
            # Update state
            await context.update_state({'issues': issues})
            
            await context.log(self.node_id, f"Identified {len(issues)} code quality issues")
            
            return NodeResult(success=True)
            
        except Exception as e:
            error_msg = f"Failed to analyze code issues: {str(e)}"
            await context.log(self.node_id, error_msg, "ERROR")
            return NodeResult(success=False, error_message=error_msg)


class SuggestNode(Node):
    """Node that generates intelligent improvement suggestions using tools."""
    
    async def execute(self, context: ExecutionContext) -> NodeResult:
        """Generate improvement suggestions and calculate quality score."""
        try:
            await context.log(self.node_id, "Generating improvement suggestions")
            
            # Get data from state
            complexity_score = context.state.complexity_score
            issues = context.state.issues
            
            # Use tool to calculate quality score
            quality_score = calculate_quality_score(complexity_score, len(issues))
            
            # Prepare metrics for suggestion generation
            metrics = {
                'lines_of_code': context.state.lines_of_code,
                'nested_blocks': context.state.nested_blocks,
                'functions_found': context.state.functions_found,
                'cyclomatic_complexity': context.state.cyclomatic_complexity,
                'complexity_score': complexity_score,
                'issues': [issue.dict() for issue in issues]
            }
            
            # Use tool to generate contextual suggestions
            suggestions = generate_improvement_suggestions(
                complexity_score, quality_score, 
                [issue.dict() for issue in issues], metrics
            )
            
            # Update state
            await context.update_state({
                'quality_score': quality_score,
                'suggestions': suggestions
            })
            
            # Get quality rating for logging
            rating, description = get_quality_rating(quality_score)
            
            await context.log(self.node_id, 
                f"Generated {len(suggestions)} suggestions, "
                f"quality score: {quality_score:.2f} ({rating})")
            
            return NodeResult(success=True)
            
        except Exception as e:
            error_msg = f"Failed to generate suggestions: {str(e)}"
            await context.log(self.node_id, error_msg, "ERROR")
            return NodeResult(success=False, error_message=error_msg)


# Register workflow nodes
def register_code_review_nodes():
    """Register all code review workflow nodes."""
    node_registry.register_node_type("extract", ExtractNode)
    node_registry.register_node_type("complexity", ComplexityNode)
    node_registry.register_node_type("issues", IssuesNode)
    node_registry.register_node_type("suggest", SuggestNode)


# Auto-register nodes when module is imported
register_code_review_nodes()