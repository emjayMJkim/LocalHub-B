def create_content_preview(
    content: str,
    max_length: int = 40,
) -> str:
    normalized_content = " ".join(content.split())

    if len(normalized_content) <= max_length:
        return normalized_content

    return normalized_content[:max_length].rstrip() + "..."