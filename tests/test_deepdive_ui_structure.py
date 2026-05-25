"""
Test to verify Deep Dive button and modal structure in dashboard.html
Task 10.1: Implement Deep Dive button and modal structure
"""
import re
from pathlib import Path


def test_deep_dive_button_exists():
    """Verify that Deep Dive button exists in idea card template"""
    dashboard_path = Path(__file__).parent.parent / "src" / "web" / "templates" / "dashboard.html"
    content = dashboard_path.read_text(encoding="utf-8")
    
    # Check for Deep Dive button in the idea card
    assert "Deep Dive ↓" in content, "Deep Dive button text not found"
    assert "openDeepDive" in content, "openDeepDive function call not found"
    assert "btn-sm" in content, "Button styling class not found"


def test_modal_overlay_structure():
    """Verify modal overlay HTML structure exists"""
    dashboard_path = Path(__file__).parent.parent / "src" / "web" / "templates" / "dashboard.html"
    content = dashboard_path.read_text(encoding="utf-8")
    
    # Check modal overlay exists
    assert 'id="deepDiveModal"' in content, "Modal overlay element not found"
    assert 'class="modal-overlay"' in content, "Modal overlay class not found"
    
    # Check modal content structure
    assert 'id="deepDiveContent"' in content, "Modal content element not found"
    assert 'class="modal-content"' in content, "Modal content class not found"
    
    # Check close button
    assert 'class="modal-close"' in content, "Modal close button not found"
    assert '&times;' in content, "Close button × symbol not found"
    
    # Check modal body
    assert 'id="deepDiveBody"' in content, "Modal body element not found"
    
    # Check spinner
    assert 'class="modal-spinner"' in content, "Modal spinner class not found"
    assert "Loading deep dive analysis" in content, "Loading message not found"


def test_modal_css_styles():
    """Verify modal CSS styles are defined"""
    dashboard_path = Path(__file__).parent.parent / "src" / "web" / "templates" / "dashboard.html"
    content = dashboard_path.read_text(encoding="utf-8")
    
    # Check modal overlay styles
    assert ".modal-overlay" in content, "Modal overlay CSS not found"
    assert "position:fixed" in content or "position: fixed" in content, "Modal overlay positioning not found"
    assert "z-index:1000" in content or "z-index: 1000" in content, "Modal z-index not found"
    
    # Check modal content styles
    assert ".modal-content" in content, "Modal content CSS not found"
    assert "max-width:700px" in content, "Modal max-width not found"
    
    # Check modal close button styles
    assert ".modal-close" in content, "Modal close button CSS not found"
    
    # Check modal spinner styles
    assert ".modal-spinner" in content, "Modal spinner CSS not found"
    assert "@keyframes spin" in content, "Spinner animation not found"


def test_modal_section_styles():
    """Verify modal section styles for content display"""
    dashboard_path = Path(__file__).parent.parent / "src" / "web" / "templates" / "dashboard.html"
    content = dashboard_path.read_text(encoding="utf-8")
    
    # Check modal section styles
    assert ".modal-section" in content, "Modal section CSS not found"
    assert ".modal-section-title" in content, "Modal section title CSS not found"
    assert ".modal-title" in content, "Modal title CSS not found"


def test_open_deep_dive_function():
    """Verify openDeepDive JavaScript function exists and is correct"""
    dashboard_path = Path(__file__).parent.parent / "src" / "web" / "templates" / "dashboard.html"
    content = dashboard_path.read_text(encoding="utf-8")
    
    # Check function exists (signature accepts optional triggerBtn param)
    assert re.search(r"function openDeepDive\(idea\b", content), "openDeepDive function not found"
    
    # Check it shows modal
    assert "modal.classList.add('visible')" in content, "Modal visibility toggle not found"
    
    # Check it fetches from API
    assert "fetch('/api/deepdive'" in content, "API fetch call not found"
    assert "method: 'POST'" in content, "POST method not found"
    assert "JSON.stringify(" in content, "Idea serialization not found"
    
    # Check it handles response (with error handling)
    assert ".then(r =>" in content, "Response handling not found"
    assert "renderModalSection" in content, "Modal section rendering not found"
    
    # Check it handles errors
    assert ".catch(err =>" in content, "Error handling not found"
    
    # Check for timeout handling (Requirement 2.11)
    assert "AbortController" in content, "AbortController not found for timeout"
    assert "setTimeout" in content, "setTimeout not found for timeout"
    
    # Check for button disabling (Requirement 2.2)
    assert "disabled = true" in content, "Button disabling not found"
    assert "disabled = false" in content, "Button re-enabling not found"
    
    # Check for error messages (Requirements 2.8, 2.11)
    assert "Failed to load Deep Dive" in content, "Error message not found"
    assert "timed out" in content or "Request timed out" in content, "Timeout message not found"


def test_close_modal_function():
    """Verify closeModal JavaScript function exists"""
    dashboard_path = Path(__file__).parent.parent / "src" / "web" / "templates" / "dashboard.html"
    content = dashboard_path.read_text(encoding="utf-8")
    
    # Check function exists
    assert "function closeModal()" in content, "closeModal function not found"
    
    # Check it removes visible class
    assert "classList.remove('visible')" in content, "Modal close logic not found"


def test_close_modal_on_overlay_function():
    """Verify closeModalOnOverlay function exists for clicking outside modal"""
    dashboard_path = Path(__file__).parent.parent / "src" / "web" / "templates" / "dashboard.html"
    content = dashboard_path.read_text(encoding="utf-8")
    
    # Check function exists
    assert "function closeModalOnOverlay" in content, "closeModalOnOverlay function not found"
    
    # Check it only closes when clicking overlay
    assert "event.target.id === 'deepDiveModal'" in content, "Overlay click detection not found"
    
    # Check modal backdrop click is wired up
    assert "deepDiveModal').addEventListener('click'" in content, "Overlay click listener not found"


def test_render_modal_section_function():
    """Verify renderModalSection helper function exists"""
    dashboard_path = Path(__file__).parent.parent / "src" / "web" / "templates" / "dashboard.html"
    content = dashboard_path.read_text(encoding="utf-8")
    
    # Check function exists
    assert "function renderModalSection(title, content, type" in content, "renderModalSection function not found"
    
    # Check it handles different types
    assert "type === 'p'" in content, "Paragraph type handling not found"
    assert "type === 'ol' || type === 'ul'" in content, "List type handling not found"
    
    # Check it creates proper HTML structure
    assert "modal-section" in content, "Modal section class not found"
    assert "modal-section-title" in content, "Modal section title class not found"


def test_deep_dive_button_in_idea_card():
    """Verify Deep Dive button is accessible via the idea detail popup"""
    dashboard_path = Path(__file__).parent.parent / "src" / "web" / "templates" / "dashboard.html"
    content = dashboard_path.read_text(encoding="utf-8")
    
    # Check addIdeaCard function exists
    assert "function addIdeaCard(idea)" in content, "addIdeaCard function not found"
    
    # Check idea card footer with action buttons exists (CSS class)
    assert "idea-card-footer" in content or "idea-actions" in content, "idea card action area not found"
    
    # Deep Dive is now in the detail popup (openIdeaDetail), not in the card directly
    assert "function openIdeaDetail(idea)" in content, "openIdeaDetail function not found"
    assert "openDeepDive(idea" in content, "openDeepDive call not found in detail popup"


def test_modal_sections_rendered():
    """Verify all required modal sections are rendered"""
    dashboard_path = Path(__file__).parent.parent / "src" / "web" / "templates" / "dashboard.html"
    content = dashboard_path.read_text(encoding="utf-8")
    
    # Check all required sections are rendered in openDeepDive
    required_sections = [
        "Research Outline",
        "Methodology",
        "Recommended Datasets",
        "Key References",
        "Estimated Timeline",
        "Recommended Tools"
    ]
    
    for section in required_sections:
        assert section in content, f"Modal section '{section}' not found"


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
