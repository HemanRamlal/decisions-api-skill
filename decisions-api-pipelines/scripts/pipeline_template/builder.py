"""Input state engineering and delimiter boundary builder."""

from typing import Any

def sanitize_text(text: str) -> str:
    """Neutralizes fake delimiter injection attacks."""
    return text.replace("<<", "< <").replace(">>", "> >")

def build_input(message_body: str, customer_metadata: dict[str, Any] | None = None) -> str:
    """
    Constructs structured input string with explicit pseudo-XML boundary markers.
    Excludes database facts that code evaluates deterministically.
    """
    clean_body = sanitize_text(message_body.strip())
    lines = []
    if customer_metadata:
        # Include only observable context questions need
        if "account_type" in customer_metadata:
            lines.append(f"ACCOUNT_TYPE: {customer_metadata['account_type']}")
    lines.append("<<MESSAGE>>")
    lines.append(clean_body)
    lines.append("<</MESSAGE>>")
    return "\n".join(lines)
