"""
Verification test for Task 4.2: Language instruction injection in generator.py
This test verifies Requirements 3.3, 3.4, 3.5
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import Mock, MagicMock
from src.core.generator import IdeaGenerator
from src.core.models import TrendAnalysis, Paper


def test_language_id_adds_indonesian_instruction():
    """
    Verifies Requirement 3.4: When language="id", the prompt should contain
    the Indonesian language instruction.
    """
    # Setup
    mock_llm = Mock()
    mock_llm.call = MagicMock(return_value='[]')  # Return empty array to avoid parsing
    mock_llm._emit = MagicMock()
    
    generator = IdeaGenerator(mock_llm)
    
    # Create a minimal trend object
    trend = TrendAnalysis(
        category="cs.AI",
        paper_count=1,
        top_keywords=["test"],
        emerging_methods=["method1"],
        research_gaps=["gap1"],
        ref_papers=[Paper(
            id="1",
            title="Test Paper",
            category="cs.AI",
            authors="Test Author",
            abstract="Test abstract",
            link="http://test.com",
            submitted_date="2024-01-01"
        )]
    )
    
    # Execute with language="id"
    generator.generate(trend, set(), n=1, research_context="", language="id")
    
    # Verify the prompt was called
    assert mock_llm.call.called, "LLM should have been called"
    
    # Get the prompt that was passed to LLM
    prompt = mock_llm.call.call_args[0][0]
    
    # Verify the Indonesian instruction is present
    assert "Bahasa Indonesia" in prompt, \
        "Prompt should contain Indonesian language instruction when language='id'"
    assert "idea_title" in prompt and "abstract" in prompt, \
        "Prompt should mention fields to translate"
    
    print("✓ Test passed: language='id' adds Indonesian instruction")


def test_language_en_no_indonesian_instruction():
    """
    Verifies Requirement 3.5: When language="en" or no language parameter,
    the prompt should NOT contain Indonesian language instruction.
    """
    # Setup
    mock_llm = Mock()
    mock_llm.call = MagicMock(return_value='[]')
    mock_llm._emit = MagicMock()
    
    generator = IdeaGenerator(mock_llm)
    
    trend = TrendAnalysis(
        category="cs.AI",
        paper_count=1,
        top_keywords=["test"],
        emerging_methods=["method1"],
        research_gaps=["gap1"],
        ref_papers=[Paper(
            id="1",
            title="Test Paper",
            category="cs.AI",
            authors="Test Author",
            abstract="Test abstract",
            link="http://test.com",
            submitted_date="2024-01-01"
        )]
    )
    
    # Test with language="en"
    generator.generate(trend, set(), n=1, research_context="", language="en")
    prompt_en = mock_llm.call.call_args[0][0]
    
    assert "Bahasa Indonesia" not in prompt_en, \
        "Prompt should NOT contain Indonesian instruction when language='en'"
    
    print("✓ Test passed: language='en' does not add Indonesian instruction")
    
    # Test with no language parameter (default)
    mock_llm.call.reset_mock()
    generator.generate(trend, set(), n=1, research_context="")
    prompt_default = mock_llm.call.call_args[0][0]
    
    assert "Bahasa Indonesia" not in prompt_default, \
        "Prompt should NOT contain Indonesian instruction when language parameter is omitted"
    
    print("✓ Test passed: default (no language param) does not add Indonesian instruction")


def test_language_instruction_placement():
    """
    Verifies Requirement 3.3: The language instruction should be properly
    placed in the prompt and not interfere with other instructions.
    """
    # Setup
    mock_llm = Mock()
    mock_llm.call = MagicMock(return_value='[]')
    mock_llm._emit = MagicMock()
    
    generator = IdeaGenerator(mock_llm)
    
    trend = TrendAnalysis(
        category="cs.AI",
        paper_count=1,
        top_keywords=["test"],
        emerging_methods=["method1"],
        research_gaps=["gap1"],
        ref_papers=[Paper(
            id="1",
            title="Test Paper",
            category="cs.AI",
            authors="Test Author",
            abstract="Test abstract",
            link="http://test.com",
            submitted_date="2024-01-01"
        )]
    )
    
    # Execute with language="id"
    generator.generate(trend, set(), n=1, research_context="test context", language="id")
    prompt = mock_llm.call.call_args[0][0]
    
    # Verify both context and language instructions are present
    assert "test context" in prompt, \
        "Context instruction should be present"
    assert "Bahasa Indonesia" in prompt, \
        "Language instruction should be present"
    assert "Generate exactly" in prompt, \
        "Main generation instruction should still be present"
    
    print("✓ Test passed: Language instruction is properly placed without interfering with other instructions")


if __name__ == "__main__":
    print("Running Task 4.2 verification tests...\n")
    
    test_language_id_adds_indonesian_instruction()
    test_language_en_no_indonesian_instruction()
    test_language_instruction_placement()
    
    print("\n✅ All verification tests passed!")
    print("\nSummary:")
    print("- ✓ Requirement 3.4: language='id' adds Indonesian instruction")
    print("- ✓ Requirement 3.5: language='en' or default does not add Indonesian instruction")
    print("- ✓ Requirement 3.3: Language instruction is properly integrated into prompt")
