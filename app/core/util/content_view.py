# 게시글 미리보기 (content 40자 요약 표시)
def create_content_preview(
    content: str,
    max_length: int = 40,
) -> str:
    normalized_content = " ".join(content.split())

    if len(normalized_content) <= max_length:
        return normalized_content

    return normalized_content[:max_length].rstrip() + "..."


# 지역 정보 address표시
# addr1과 addr2를 공백으로 연결 (두 값이 모두 없으면 None을 반환)
def combine_address(
    addr1: str | None,
    addr2: str | None,
) -> str | None:
    address_parts = [
        value.strip()
        for value in (addr1, addr2)
        if value and value.strip()
    ]

    if not address_parts:
        return None

    return " ".join(address_parts)


# 지역 정보 image 반환
# firstimage가 있으면 우선 사용 -> 없으면 firstimage2를 사용
def select_image_url(
    firstimage: str | None,
    firstimage2: str | None,
) -> str | None:
    if firstimage and firstimage.strip():
        return firstimage.strip()

    if firstimage2 and firstimage2.strip():
        return firstimage2.strip()

    return None