import os

def save_draft_to_file(topic: str, content: str) -> str:
    """Tool to save the audited final draft locally as a Markdown file."""
    safe_name = "".join(c if c.isalnum() else "_" for c in topic[:30]).strip("_")
    filename = f"draft_{safe_name}.md"
    os.makedirs("drafts", exist_ok=True)
    filepath = os.path.join("drafts", filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    return filepath
