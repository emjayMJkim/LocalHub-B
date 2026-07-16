CATEGORY_NAME = {
    "DEFAULT": "전체",
    "TOURISM": "관광지",
    "LEISURE": "레포츠",
    "CULTURAL_FACILITY": "문화시설",
    "SHOPPING": "쇼핑",
    "ACCOMMODATION": "숙박",
    "TRAVEL_COURSE": "여행코스",
    "RESTAURANT": "음식점",
    "FESTIVAL": "축제공연행사",
}

CATEGORY_LIST = CATEGORY_NAME.keys()

CONTENT_TYPE_CATEGORY: dict[str, str] = {
    content_type: category
    for category, content_type in CATEGORY_NAME.items()
}


def get_category_name(category: str) -> str:
    return CATEGORY_NAME.get(category.upper(), "")

def get_category_code_by_content_type(
    content_type: str,
) -> str:
    return CONTENT_TYPE_CATEGORY.get(content_type, "")