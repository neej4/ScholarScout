"""
Manual Verification Test for Task 7.2: Research Context in startPipeline()

This test verifies that:
1. startPipeline() reads researchContext.value.slice(0, 2000)
2. research_context is included in the payload to POST /api/run
3. textarea is not cleared after pipeline completion

Requirements: 1.4, 1.7
"""

import re
from pathlib import Path


def test_research_context_implementation():
    """Verify that startPipeline() correctly reads and sends research_context"""
    
    dashboard_path = Path(__file__).parent.parent / "src" / "web" / "templates" / "dashboard.html"
    
    assert dashboard_path.exists(), f"Dashboard file not found at {dashboard_path}"
    
    content = dashboard_path.read_text(encoding='utf-8')
    
    # Test 1: Verify textarea element exists with correct id and placeholder
    assert 'id="researchContext"' in content, "researchContext textarea not found"
    assert 'placeholder=' in content and 'researchContext' in content, \
        "researchContext textarea should have a placeholder"
    
    # Test 2: Verify startPipeline() reads researchContext with slice(0, 2000)
    # Look for the pattern: document.getElementById('researchContext').value.slice(0, 2000)
    pattern = r"document\.getElementById\(['\"]researchContext['\"]\)\.value\.slice\(0,\s*2000\)"
    match = re.search(pattern, content)
    assert match is not None, \
        "startPipeline() does not read researchContext.value.slice(0, 2000). " \
        "Found pattern should be: document.getElementById('researchContext').value.slice(0, 2000)"
    
    # Test 3: Verify research_context is included in fetch payload
    # Look for the pattern in the fetch body
    fetch_pattern = r"body:\s*JSON\.stringify\(\{[^}]*research_context:\s*research_context[^}]*\}\)"
    fetch_match = re.search(fetch_pattern, content, re.DOTALL)
    assert fetch_match is not None, \
        "research_context is not included in the fetch payload to /api/run"
    
    # Test 4: Verify textarea is NOT cleared after pipeline completion
    # Check that there's no code that sets researchContext.value = ''
    clear_patterns = [
        r"researchContext\.value\s*=\s*['\"]",
        r"getElementById\(['\"]researchContext['\"]\)\.value\s*=\s*['\"]",
    ]
    
    for pattern in clear_patterns:
        match = re.search(pattern, content)
        assert match is None, \
            f"Found code that clears researchContext textarea: {match.group(0) if match else 'N/A'}"
    
    # Test 5: Verify the done event handler doesn't clear the textarea
    # Extract the 'done' event handler
    done_handler_pattern = r"else if \(e === ['\"]done['\"]\)\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}"
    done_match = re.search(done_handler_pattern, content, re.DOTALL)
    
    if done_match:
        done_handler_code = done_match.group(1)
        assert 'researchContext' not in done_handler_code, \
            "The 'done' event handler should not reference researchContext"
    
    print("✅ All verifications passed!")
    print("✅ startPipeline() reads researchContext.value.slice(0, 2000)")
    print("✅ research_context is included in POST /api/run payload")
    print("✅ textarea is not cleared after pipeline completion")


if __name__ == "__main__":
    test_research_context_implementation()
    print("\n✅ Task 7.2 verification complete!")
