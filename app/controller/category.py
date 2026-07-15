from app.core.util.constants import CATEGORY_NAME


class CategoryController:
    @staticmethod
    def get_categories() -> list[dict[str, str]]:
        return [
            {
                "code": code,
                "name": name,
            }
            for code, name in CATEGORY_NAME.items()
        ]