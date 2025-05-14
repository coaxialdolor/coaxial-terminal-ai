"""Utilities for processing user queries."""
import re

def preprocess_query(query):
    """Preprocess user queries to clarify potentially ambiguous requests.

    Args:
        query: The original user query

    Returns:
        Potentially enhanced query with clarifications
    """
    if not query:
        return query

    # Check for desktop-related queries that might be misinterpreted
    desktop_keywords = ["desktop", "Desktop"]
    location_indicators = ["on my", "in my", "list", "show", "find", "files"]

    has_desktop_keyword = any(keyword in query for keyword in desktop_keywords)
    has_location_indicator = any(indicator in query for indicator in location_indicators)

    # Pattern for current directory references
    current_dir_pattern = re.compile(r'\b(this|current|present)\s+(directory|dir|folder)\b', re.IGNORECASE)
    has_current_dir_reference = bool(current_dir_pattern.search(query))

    # If query mentions desktop as a location and doesn't clearly specify current directory
    if has_desktop_keyword and has_location_indicator and not has_current_dir_reference:
        # Check if query already contains proper path references
        if "~/Desktop" in query or "%USERPROFILE%\\Desktop" in query:
            return query  # Already has proper path reference
        else:
            # Add clarification that we mean the actual Desktop folder
            return f"{query} (specifically the ~/Desktop folder, not the current directory)"

    return query