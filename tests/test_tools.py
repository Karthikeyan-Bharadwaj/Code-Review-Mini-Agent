"""
Tests for code analysis tools.

These tests verify the core analysis functionality that powers the workflow nodes.
"""

import pytest
import ast
import sys
import os

# Add project root to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import (
    parse_python_code,
    count_lines_of_code,
    calculate_complexity_score,
    calculate_quality_score,
    detect_code_smells,
    get_quality_rating,
    generate_improvement_suggestions
)


class TestCodeAnalysisTools:
    """Test suite for code analysis tools."""
    
    def test_count_lines_of_code_simple(self):
        """Test line counting with simple code."""
        code = """def hello():
    print("world")
    return True"""
        
        result = count_lines_of_code(code)
        assert result == 3
    
    def test_count_lines_of_code_with_comments(self):
        """Test line counting ignores comments."""
        code = """# This is a comment
def hello():
    # Another comment
    print("world")
    return True"""
        
        result = count_lines_of_code(code)
        assert result == 3  # Comments should be ignored
    
    def test_parse_python_code_comprehensive(self):
        """Test comprehensive code parsing."""
        code = """def calculate_sum(numbers):
    # TODO: Add input validation
    total = 0
    for num in numbers:
        if num > 0:
            total += num
    print(f"Sum: {total}")
    return total"""
        
        result = parse_python_code(code)
        
        # Verify all expected metrics are present
        assert 'lines_of_code' in result
        assert 'functions_found' in result
        assert 'cyclomatic_complexity' in result
        assert 'todo_comments' in result
        assert 'print_statements' in result
        
        # Verify specific values
        assert result['functions_found'] == 1
        assert result['lines_of_code'] == 7
        assert len(result['todo_comments']) == 1
        assert len(result['print_statements']) == 1
    
    def test_complexity_score_calculation(self):
        """Test complexity score formula."""
        # Test with known values
        lines_of_code = 10
        nested_blocks = 2
        long_names = ["very_long_variable_name_that_exceeds_threshold"]
        
        result = calculate_complexity_score(lines_of_code, nested_blocks, long_names)
        
        # Formula: 100 - (lines_of_code * 0.8 + nested_blocks * 5 + long_names * 2)
        expected = 100 - (10 * 0.8 + 2 * 5 + 1 * 2)
        assert result == expected
        assert 0 <= result <= 100  # Score should be bounded
    
    def test_quality_score_calculation(self):
        """Test quality score formula."""
        complexity_score = 75.0
        num_issues = 3
        
        result = calculate_quality_score(complexity_score, num_issues)
        
        # Formula: complexity_score - 10 * num_issues
        expected = 75.0 - (10 * 3)
        assert result == expected
        assert result >= 0  # Score should not go below 0
    
    def test_quality_rating_categories(self):
        """Test quality rating categorization."""
        test_cases = [
            (90, "Excellent"),
            (70, "Good"),
            (50, "Fair"),
            (30, "Poor"),
            (10, "Very Poor")
        ]
        
        for score, expected_rating in test_cases:
            rating, description = get_quality_rating(score)
            assert rating == expected_rating
            assert isinstance(description, str)
            assert len(description) > 0
    
    def test_detect_code_smells_comprehensive(self):
        """Test comprehensive code smell detection."""
        code = """def problematic_function():
    # TODO: Fix this function
    print("Debug output")
    very_long_line_that_exceeds_the_recommended_length_and_should_be_flagged_as_a_style_issue_by_our_detector = True
    try:
        for i in range(10):
            for j in range(10):
                for k in range(10):  # Deep nesting
                    pass
    except:  # Bare except
        pass"""
        
        # Parse code to get metrics
        metrics = parse_python_code(code)
        
        # Detect issues
        issues = detect_code_smells(code, metrics)
        
        # Verify different types of issues are detected
        issue_types = [issue['type'] for issue in issues]
        assert 'style' in issue_types  # Long line
        assert 'structure' in issue_types  # Bare except or nesting
        assert 'maintenance' in issue_types  # TODO comment
        
        # Verify all issues have required fields
        for issue in issues:
            assert 'type' in issue
            assert 'severity' in issue
            assert 'description' in issue
            assert 'suggestion' in issue
    
    def test_generate_improvement_suggestions(self):
        """Test suggestion generation logic."""
        complexity_score = 60.0
        quality_score = 45.0
        issues = [
            {'type': 'complexity', 'severity': 'high'},
            {'type': 'style', 'severity': 'low'}
        ]
        metrics = {
            'lines_of_code': 50,
            'functions_found': 2,
            'cyclomatic_complexity': 8
        }
        
        suggestions = generate_improvement_suggestions(
            complexity_score, quality_score, issues, metrics
        )
        
        # Verify suggestions are generated
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # Verify all suggestions are strings
        for suggestion in suggestions:
            assert isinstance(suggestion, str)
            assert len(suggestion) > 0
        
        # Verify no duplicates
        assert len(suggestions) == len(set(suggestions))


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_code_parsing(self):
        """Test parsing empty or whitespace-only code."""
        empty_code = ""
        whitespace_code = "   \n\n   "
        
        # Should not raise exceptions
        result1 = parse_python_code(empty_code)
        result2 = parse_python_code(whitespace_code)
        
        assert result1['lines_of_code'] == 0
        assert result2['lines_of_code'] == 0
    
    def test_invalid_syntax_handling(self):
        """Test handling of invalid Python syntax."""
        invalid_code = "def broken_function(\n    # Missing closing parenthesis"
        
        # Should raise SyntaxError
        with pytest.raises(SyntaxError):
            parse_python_code(invalid_code)
    
    def test_boundary_values(self):
        """Test boundary values for scoring functions."""
        # Test minimum complexity score
        result = calculate_complexity_score(1000, 100, ["long"] * 50)
        assert result == 0.0  # Should not go below 0
        
        # Test maximum complexity score
        result = calculate_complexity_score(0, 0, [])
        assert result == 100.0
        
        # Test minimum quality score
        result = calculate_quality_score(0, 100)
        assert result == 0.0  # Should not go below 0


if __name__ == "__main__":
    pytest.main([__file__])