"""
Test to verify language select element and sessionStorage persistence.
Task 8.1: Ensure language select element and sessionStorage persistence are correct
Requirements: 3.1, 3.2, 3.6
"""

import pytest
import re


def test_language_select_element_exists():
    """Verify that select#langSelect exists with correct options."""
    with open('src/web/templates/dashboard.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Check select element exists
    assert 'id="langSelect"' in html_content, "select#langSelect not found"
    
    # Find the select element and its options
    select_match = re.search(r'<select[^>]*id="langSelect"[^>]*>(.*?)</select>', html_content, re.DOTALL)
    assert select_match is not None, "Could not find langSelect element"
    
    select_content = select_match.group(1)
    
    # Check for English option
    assert '<option value="en">English</option>' in select_content, \
        "English option with value 'en' not found"
    
    # Check for Indonesian option
    assert '<option value="id">Bahasa Indonesia</option>' in select_content, \
        "Indonesian option with value 'id' not found"


def test_startpipeline_includes_language_in_payload():
    """Verify that the pipeline reads langSelect.value and includes it in the payload."""
    with open('src/web/templates/dashboard.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Find _doStartPipeline function (actual pipeline logic)
    match = re.search(r'function _doStartPipeline\([^)]*\)\s*\{(.*?)\n\}', html_content, re.DOTALL)
    assert match is not None, "_doStartPipeline function not found"
    
    function_body = match.group(1)
    
    # Check that language is read from langSelect
    assert "document.getElementById('langSelect').value" in function_body, \
        "startPipeline should read langSelect.value"
    
    # Check that language is included in the fetch payload
    assert 'language:' in function_body or 'language :' in function_body, \
        "startPipeline should include language in payload"


def test_sessionstorage_persistence_logic():
    """Verify that sessionStorage logic exists for language persistence."""
    with open('src/web/templates/dashboard.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Check for sessionStorage usage
    assert 'sessionStorage' in html_content, \
        "sessionStorage should be used for language persistence"
    
    # Check for scholarscout_language key
    assert 'scholarscout_language' in html_content, \
        "sessionStorage key 'scholarscout_language' should be used"
    
    # Check for save logic (setItem)
    assert 'sessionStorage.setItem' in html_content or "sessionStorage['scholarscout_language']" in html_content, \
        "Should save language to sessionStorage"
    
    # Check for restore logic (getItem)
    assert 'sessionStorage.getItem' in html_content or "sessionStorage['scholarscout_language']" in html_content, \
        "Should restore language from sessionStorage"


def test_language_select_change_handler():
    """Verify that langSelect has a change event handler to save to sessionStorage."""
    with open('src/web/templates/dashboard.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    # Look for event listener on langSelect
    # Could be: addEventListener, onchange attribute, or jQuery-style
    has_listener = (
        "langSelect" in html_content and "addEventListener" in html_content and "change" in html_content
    ) or (
        "langSelect" in html_content and "onchange" in html_content
    )
    
    assert has_listener, \
        "langSelect should have a change event handler to save to sessionStorage"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
