from app.domains.servicenow.schemas import FieldName


def is_customer_facing_field(field_name: FieldName) -> bool:
    return field_name == "additional_comments"


def is_internal_field(field_name: FieldName) -> bool:
    return field_name == "work_notes"
