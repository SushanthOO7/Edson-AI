SUPPORTED_FIELDS = ("short_description", "description", "additional_comments", "work_notes")

CUSTOMER_VISIBLE_FIELDS = {"additional_comments"}
INTERNAL_FIELDS = {"work_notes"}


def field_visibility(field_name: str) -> str:
    if field_name in CUSTOMER_VISIBLE_FIELDS:
        return "customer_safe"
    if field_name in INTERNAL_FIELDS:
        return "internal"
    return "template"
