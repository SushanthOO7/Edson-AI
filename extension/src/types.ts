export type SupportedFieldName = "short_description" | "description" | "additional_comments" | "work_notes";

export type FieldStatus =
  | "Ready"
  | "Generating"
  | "AI Generated"
  | "AI Revised"
  | "Reverted"
  | "Accepted"
  | "Manual Edit Detected"
  | "Error";

export interface TicketContext {
  ticket_type?: string;
  number?: string;
  requested_for?: string;
  campus?: string;
  building?: string;
  room_number?: string;
  location?: string;
  room?: string;
  item?: string;
  more_information?: string;
  recent_activity?: string;
  additional_details?: string;
  current_short_description?: string;
  current_description?: string;
  current_additional_comments?: string;
  current_work_notes?: string;
  [key: string]: string | undefined;
}

export interface GeneratedFieldsResponse {
  short_description: string;
  description: string;
  additional_comments: string;
  work_notes: string;
  missing_info: string[];
  suggested_next_action: string;
  confidence: "low" | "medium" | "high";
  needs_review: boolean;
}

export interface RevisedFieldResponse {
  field_name: SupportedFieldName;
  revised_value: string;
  confidence: "low" | "medium" | "high";
  needs_review: boolean;
}

export interface FieldStatusResponse {
  saved: boolean;
  field_name: SupportedFieldName;
  status: "generated" | "revised" | "accepted" | "manual_edit_detected" | "error";
  accepted_example_saved: boolean;
}
