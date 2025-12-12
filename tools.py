"""
Code analysis tools and helper functions for the Code Review Mini-Agent.

This module contains all the core analysis functions that workflow nodes use.
Separating these tools makes the workflow nodes cleaner and more modular.
"""

import ast
import re
from typing import List, Dict, Any, Tuple


# =============================================================================
# EXTRACTION TOOLS
# =============================================================================

def parse_python_code(source_code: str) -> Dict[str, Any]:
    """Parse Python source code and extract comprehensive metrics.
    
    Args:
        source_code: Python source code as string
        
    Returns:
        Dictionary containing all extracted metrics
        
    Raises:
        SyntaxError: If code cannot be parsed
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        raise SyntaxError(f"Failed to parse Python code: {str(e)}")
    
    metrics = {
        'lines_of_code': count_lines_of_code(source_code),
        'nested_blocks': count_nested_blocks(tree),
        'long_names': find_long_names(tree),
        'cyclomatic_complexity': calculate_cyclomatic_complexity(tree),
        'functions_found': count_functions(tree),
        'classes_found': count_classes(tree),
        'todo_comments': detect_todo_comments(source_code),
        'print_statements': detect_print_statements(tree),
        'bare_exceptions': detect_bare_exceptions(tree),
    }
    return metrics


def count_lines_of_code(source_code: str) -> int:
    """Count non-empty, non-comment lines of code.
    
    Args:
        source_code: Python source code as string
        
    Returns:
        Number of lines of code
    """
    lines = source_code.split('\n')
    loc = 0
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith('#'):
            loc += 1
    return loc


def count_functions(tree: ast.AST) -> int:
    """Count the number of function definitions in the code.
    
    Args:
        tree: AST tree of the code
        
    Returns:
        Number of functions found
    """
    class FunctionCounter(ast.NodeVisitor):
        def __init__(self):
            self.count = 0
        
        def visit_FunctionDef(self, node):
            self.count += 1
            self.generic_visit(node)
        
        def visit_AsyncFunctionDef(self, node):
            self.count += 1
            self.generic_visit(node)
    
    counter = FunctionCounter()
    counter.visit(tree)
    return counter.count


def count_classes(tree: ast.AST) -> int:
    """Count the number of class definitions in the code.
    
    Args:
        tree: AST tree of the code
        
    Returns:
        Number of classes found
    """
    class ClassCounter(ast.NodeVisitor):
        def __init__(self):
            self.count = 0
        
        def visit_ClassDef(self, node):
            self.count += 1
            self.generic_visit(node)
    
    counter = ClassCounter()
    counter.visit(tree)
    return counter.count


# =============================================================================
# COMPLEXITY ANALYSIS TOOLS
# =============================================================================

def count_nested_blocks(tree: ast.AST) -> int:
    """Count nested control structures in the code.
    
    Args:
        tree: AST tree of the code
        
    Returns:
        Number of nested blocks
    """
    class NestedBlockVisitor(ast.NodeVisitor):
        def __init__(self):
            self.depth = 0
            self.nested_blocks = 0
        
        def visit_control_structure(self, node):
            self.depth += 1
            if self.depth > 1:
                self.nested_blocks += 1
            self.generic_visit(node)
            self.depth -= 1
        
        visit_If = visit_control_structure
        visit_For = visit_control_structure
        visit_While = visit_control_structure
        visit_Try = visit_control_structure
        visit_With = visit_control_structure
        visit_FunctionDef = visit_control_structure
        visit_AsyncFunctionDef = visit_control_structure
        visit_ClassDef = visit_control_structure
    
    visitor = NestedBlockVisitor()
    visitor.visit(tree)
    return visitor.nested_blocks


def calculate_cyclomatic_complexity(tree: ast.AST) -> int:
    """Calculate cyclomatic complexity of the code.
    
    Cyclomatic complexity measures the number of linearly independent paths
    through the program's source code.
    
    Args:
        tree: AST tree of the code
        
    Returns:
        Cyclomatic complexity score
    """
    class ComplexityVisitor(ast.NodeVisitor):
        def __init__(self):
            self.complexity = 1  # Base complexity
        
        def visit_If(self, node):
            self.complexity += 1
            # Count elif branches
            if hasattr(node, 'orelse') and node.orelse:
                if isinstance(node.orelse[0], ast.If):
                    # This is an elif, don't double count
                    pass
                else:
                    # This is an else, add 1
                    self.complexity += 1
            self.generic_visit(node)
        
        def visit_For(self, node):
            self.complexity += 1
            self.generic_visit(node)
        
        def visit_While(self, node):
            self.complexity += 1
            self.generic_visit(node)
        
        def visit_Try(self, node):
            # Add complexity for each exception handler
            self.complexity += len(node.handlers)
            self.generic_visit(node)
        
        def visit_BoolOp(self, node):
            # Add complexity for boolean operations (and/or)
            self.complexity += len(node.values) - 1
            self.generic_visit(node)
        
        def visit_comprehension(self, node):
            # List/dict/set comprehensions add complexity
            self.complexity += 1
            self.generic_visit(node)
        
        visit_ListComp = visit_comprehension
        visit_DictComp = visit_comprehension
        visit_SetComp = visit_comprehension
        visit_GeneratorExp = visit_comprehension
    
    visitor = ComplexityVisitor()
    visitor.visit(tree)
    return visitor.complexity


def calculate_complexity_score(lines_of_code: int, nested_blocks: int, long_names: List[str]) -> float:
    """Calculate complexity score using the specified formula.
    
    Formula: 100 - (lines_of_code * 0.8 + nested_blocks * 5 + long_names * 2)
    
    Args:
        lines_of_code: Number of lines of code
        nested_blocks: Number of nested blocks
        long_names: List of long variable/function names
        
    Returns:
        Complexity score (0-100)
    """
    long_name_penalty = len(long_names)
    score = 100 - (lines_of_code * 0.8 + nested_blocks * 5 + long_name_penalty * 2)
    return max(0.0, min(100.0, score))


# =============================================================================
# ISSUE DETECTION TOOLS
# =============================================================================

def find_long_names(tree: ast.AST, threshold: int = 20) -> List[str]:
    """Find variable and function names longer than threshold.
    
    Args:
        tree: AST tree of the code
        threshold: Maximum acceptable name length
        
    Returns:
        List of long names found
    """
    long_names = []
    
    class NameVisitor(ast.NodeVisitor):
        def visit_Name(self, node):
            if len(node.id) > threshold:
                long_names.append(node.id)
            self.generic_visit(node)
        
        def visit_FunctionDef(self, node):
            if len(node.name) > threshold:
                long_names.append(node.name)
            self.generic_visit(node)
        
        def visit_AsyncFunctionDef(self, node):
            if len(node.name) > threshold:
                long_names.append(node.name)
            self.generic_visit(node)
        
        def visit_ClassDef(self, node):
            if len(node.name) > threshold:
                long_names.append(node.name)
            self.generic_visit(node)
    
    visitor = NameVisitor()
    visitor.visit(tree)
    return list(set(long_names))  # Remove duplicates


def detect_todo_comments(source_code: str) -> List[Dict[str, Any]]:
    """Detect TODO, FIXME, and similar comments in the code.
    
    Args:
        source_code: Python source code as string
        
    Returns:
        List of dictionaries containing TODO information
    """
    todo_patterns = [
        r'#.*TODO',
        r'#.*FIXME',
        r'#.*HACK',
        r'#.*BUG',
        r'#.*NOTE',
        r'#.*XXX'
    ]
    
    todos = []
    lines = source_code.split('\n')
    
    for i, line in enumerate(lines, 1):
        for pattern in todo_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                todos.append({
                    'line_number': i,
                    'content': line.strip(),
                    'type': 'todo_comment'
                })
                break  # Only count each line once
    
    return todos


def detect_print_statements(tree: ast.AST) -> List[Dict[str, Any]]:
    """Detect print statements in the code.
    
    Args:
        tree: AST tree of the code
        
    Returns:
        List of dictionaries containing print statement information
    """
    class PrintDetector(ast.NodeVisitor):
        def __init__(self):
            self.prints = []
        
        def visit_Call(self, node):
            if (isinstance(node.func, ast.Name) and 
                node.func.id == 'print'):
                self.prints.append({
                    'line_number': node.lineno,
                    'type': 'print_statement'
                })
            self.generic_visit(node)
    
    detector = PrintDetector()
    detector.visit(tree)
    return detector.prints


def detect_bare_exceptions(tree: ast.AST) -> List[Dict[str, Any]]:
    """Detect bare except clauses in the code.
    
    Args:
        tree: AST tree of the code
        
    Returns:
        List of dictionaries containing bare exception information
    """
    class BareExceptDetector(ast.NodeVisitor):
        def __init__(self):
            self.bare_excepts = []
        
        def visit_ExceptHandler(self, node):
            if node.type is None:  # Bare except clause
                self.bare_excepts.append({
                    'line_number': node.lineno,
                    'type': 'bare_exception'
                })
            self.generic_visit(node)
    
    detector = BareExceptDetector()
    detector.visit(tree)
    return detector.bare_excepts


def detect_code_smells(source_code: str, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Detect various code quality issues using rule-based patterns.
    
    Args:
        source_code: Python source code as string
        metrics: Dictionary of code metrics
        
    Returns:
        List of dictionaries containing issue information
    """
    issues = []
    lines = source_code.split('\n')
    
    # Check for long lines
    for i, line in enumerate(lines, 1):
        if len(line) > 100:
            issues.append({
                'type': 'style',
                'severity': 'low',
                'line_number': i,
                'description': f"Line too long ({len(line)} characters)",
                'suggestion': "Break long lines to improve readability"
            })
    
    # Check for high cyclomatic complexity
    complexity = metrics.get('cyclomatic_complexity', 0)
    if complexity > 10:
        issues.append({
            'type': 'complexity',
            'severity': 'high',
            'line_number': None,
            'description': f"High cyclomatic complexity ({complexity})",
            'suggestion': "Reduce complexity by extracting methods or simplifying logic"
        })
    elif complexity > 7:
        issues.append({
            'type': 'complexity',
            'severity': 'medium',
            'line_number': None,
            'description': f"Moderate cyclomatic complexity ({complexity})",
            'suggestion': "Consider simplifying logic to improve maintainability"
        })
    
    # Check for too many nested blocks
    nested_blocks = metrics.get('nested_blocks', 0)
    if nested_blocks > 5:
        issues.append({
            'type': 'structure',
            'severity': 'medium',
            'line_number': None,
            'description': f"Too many nested blocks ({nested_blocks})",
            'suggestion': "Reduce nesting by using early returns or extracting methods"
        })
    elif nested_blocks > 3:
        issues.append({
            'type': 'structure',
            'severity': 'low',
            'line_number': None,
            'description': f"High nesting level ({nested_blocks})",
            'suggestion': "Consider reducing nesting for better readability"
        })
    
    # Check for long variable names
    long_names = metrics.get('long_names', [])
    if long_names:
        issues.append({
            'type': 'naming',
            'severity': 'low',
            'line_number': None,
            'description': f"Found {len(long_names)} overly long names",
            'suggestion': "Consider using shorter, more concise variable names"
        })
    
    # Check for TODO comments
    todos = metrics.get('todo_comments', [])
    if todos:
        issues.append({
            'type': 'maintenance',
            'severity': 'low',
            'line_number': None,
            'description': f"Found {len(todos)} TODO/FIXME comments",
            'suggestion': "Address TODO comments or convert to proper issues"
        })
    
    # Check for print statements
    prints = metrics.get('print_statements', [])
    if prints:
        issues.append({
            'type': 'style',
            'severity': 'low',
            'line_number': None,
            'description': f"Found {len(prints)} print statements",
            'suggestion': "Replace print statements with proper logging"
        })
    
    # Check for bare exceptions
    bare_excepts = metrics.get('bare_exceptions', [])
    if bare_excepts:
        issues.append({
            'type': 'structure',
            'severity': 'medium',
            'line_number': None,
            'description': f"Found {len(bare_excepts)} bare except clauses",
            'suggestion': "Specify exception types instead of using bare except"
        })
    
    return issues


# =============================================================================
# QUALITY SCORING TOOLS
# =============================================================================

def calculate_quality_score(complexity_score: float, num_issues: int) -> float:
    """Calculate overall quality score using the specified formula.
    
    Formula: complexity_score - 10 * num_issues
    
    Args:
        complexity_score: Complexity score (0-100)
        num_issues: Number of issues found
        
    Returns:
        Quality score (0-100)
    """
    score = complexity_score - 10 * num_issues
    return max(0.0, score)


def get_quality_rating(quality_score: float) -> Tuple[str, str]:
    """Get quality rating and description based on score.
    
    Args:
        quality_score: Quality score (0-100)
        
    Returns:
        Tuple of (rating, description)
    """
    if quality_score >= 80:
        return ("Excellent", "Code quality is excellent with minimal issues")
    elif quality_score >= 60:
        return ("Good", "Code quality is good with minor improvements needed")
    elif quality_score >= 40:
        return ("Fair", "Code quality is fair, several improvements recommended")
    elif quality_score >= 20:
        return ("Poor", "Code quality is poor, significant refactoring needed")
    else:
        return ("Very Poor", "Code quality is very poor, major refactoring required")


# =============================================================================
# SUGGESTION GENERATION TOOLS
# =============================================================================

def generate_improvement_suggestions(complexity_score: float, quality_score: float, 
                                   issues: List[Dict[str, Any]], metrics: Dict[str, Any]) -> List[str]:
    """Generate contextual improvement suggestions based on analysis results.
    
    Args:
        complexity_score: Complexity score (0-100)
        quality_score: Quality score (0-100)
        issues: List of identified issues
        metrics: Dictionary of code metrics
        
    Returns:
        List of improvement suggestions
    """
    suggestions = []
    
    # Quality-based suggestions
    if quality_score < 20:
        suggestions.append("This code requires major refactoring to improve quality")
        suggestions.append("Consider breaking down complex functions into smaller, focused methods")
    elif quality_score < 40:
        suggestions.append("This code needs significant improvements to reach good quality")
        suggestions.append("Focus on addressing the highest severity issues first")
    elif quality_score < 60:
        suggestions.append("Code quality is fair - addressing identified issues will improve maintainability")
    elif quality_score < 80:
        suggestions.append("Code quality is good - minor improvements will make it excellent")
    else:
        suggestions.append("Excellent code quality! Consider this as a reference for other modules")
    
    # Issue-specific suggestions
    issue_types = set(issue['type'] for issue in issues)
    
    if 'complexity' in issue_types:
        suggestions.append("Reduce cyclomatic complexity by extracting methods or simplifying conditional logic")
    
    if 'structure' in issue_types:
        suggestions.append("Improve code structure by reducing nesting and using early returns")
    
    if 'style' in issue_types:
        suggestions.append("Follow PEP 8 style guidelines for better code readability")
    
    if 'naming' in issue_types:
        suggestions.append("Use more concise and descriptive variable names")
    
    if 'maintenance' in issue_types:
        suggestions.append("Address TODO comments and technical debt items")
    
    # Metric-based suggestions
    if metrics.get('functions_found', 0) == 0:
        suggestions.append("Consider organizing code into functions for better modularity")
    
    if metrics.get('lines_of_code', 0) > 50:
        suggestions.append("Consider breaking large code blocks into smaller, focused functions")
    
    # Remove duplicates while preserving order
    seen = set()
    unique_suggestions = []
    for suggestion in suggestions:
        if suggestion not in seen:
            seen.add(suggestion)
            unique_suggestions.append(suggestion)
    
    return unique_suggestions


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def format_analysis_summary(metrics: Dict[str, Any], quality_score: float) -> Dict[str, Any]:
    """Format analysis results into a clean summary.
    
    Args:
        metrics: Dictionary of code metrics
        quality_score: Overall quality score
        
    Returns:
        Formatted summary dictionary
    """
    rating, description = get_quality_rating(quality_score)
    
    return {
        'quality_score': round(quality_score, 1),
        'rating': rating,
        'description': description,
        'summary': {
            'functions_found': metrics.get('functions_found', 0),
            'lines_of_code': metrics.get('lines_of_code', 0),
            'complexity_score': round(metrics.get('complexity_score', 0), 1),
            'cyclomatic_complexity': metrics.get('cyclomatic_complexity', 0),
            'nested_blocks': metrics.get('nested_blocks', 0),
            'total_issues': len(metrics.get('issues', [])),
            'improvement_suggestions': len(metrics.get('suggestions', []))
        }
    }