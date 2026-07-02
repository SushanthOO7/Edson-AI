import type {
  FieldStatusResponse,
  GeneratedFieldsResponse,
  RevisedFieldResponse,
  SupportedFieldName,
  TicketContext
} from "./types";

type ExtensionApiResponse<TResponse> =
  | {
      ok: true;
      data: TResponse;
    }
  | {
      ok: false;
      error: string;
    };

async function postJson<TResponse>(path: string, body: unknown): Promise<TResponse> {
  if (!canUseExtensionRuntime()) {
    throw new Error("The extension background worker is not available.");
  }

  const response = (await chrome.runtime.sendMessage({
    type: "EDSON_API_POST",
    path,
    body
  })) as ExtensionApiResponse<TResponse> | undefined;

  if (!response) {
    throw new Error("The extension background worker did not respond.");
  }
  if (!response.ok) {
    throw new Error(response.error);
  }
  return response.data;
}

function canUseExtensionRuntime(): boolean {
  return (
    typeof chrome !== "undefined" &&
    Boolean(chrome.runtime?.id) &&
    typeof chrome.runtime.sendMessage === "function"
  );
}

export function generateFields(ticketContext: TicketContext): Promise<GeneratedFieldsResponse> {
  return postJson<GeneratedFieldsResponse>("/api/servicenow/generate-fields", {
    ticket_context: ticketContext,
    user_instruction: "Generate all fields."
  });
}

export function generateShortDescription(ticketContext: TicketContext): Promise<GeneratedFieldsResponse> {
  return postJson<GeneratedFieldsResponse>("/api/servicenow/generate-short-description", {
    ticket_context: ticketContext
  });
}

export function generateDescription(ticketContext: TicketContext): Promise<GeneratedFieldsResponse> {
  return postJson<GeneratedFieldsResponse>("/api/servicenow/generate-description", {
    ticket_context: ticketContext
  });
}

export function generateAdditionalComments(ticketContext: TicketContext): Promise<GeneratedFieldsResponse> {
  return postJson<GeneratedFieldsResponse>("/api/servicenow/generate-additional-comments", {
    ticket_context: ticketContext
  });
}

export function generateWorkNotes(ticketContext: TicketContext): Promise<GeneratedFieldsResponse> {
  return postJson<GeneratedFieldsResponse>("/api/servicenow/generate-work-notes", {
    ticket_context: ticketContext
  });
}

export function generateField(
  ticketContext: TicketContext,
  fieldName: SupportedFieldName
): Promise<GeneratedFieldsResponse> {
  const generators: Record<SupportedFieldName, (context: TicketContext) => Promise<GeneratedFieldsResponse>> = {
    short_description: generateShortDescription,
    description: generateDescription,
    additional_comments: generateAdditionalComments,
    work_notes: generateWorkNotes
  };
  return generators[fieldName](ticketContext);
}

export function reviseField(args: {
  ticketNumber?: string;
  fieldName: SupportedFieldName;
  currentFieldValue: string;
  revisionInstruction: string;
  ticketContext: TicketContext;
}): Promise<RevisedFieldResponse> {
  return postJson<RevisedFieldResponse>("/api/servicenow/revise-field", {
    ticket_number: args.ticketNumber,
    field_name: args.fieldName,
    current_field_value: args.currentFieldValue,
    revision_instruction: args.revisionInstruction,
    ticket_context: args.ticketContext
  });
}

export function saveFieldStatus(args: {
  ticketNumber?: string;
  ticketType?: string;
  fieldName: SupportedFieldName;
  status: "generated" | "revised" | "accepted" | "manual_edit_detected" | "error";
  finalValue: string;
  source: "ai_generated" | "ai_revised" | "manual" | "system";
  ticketSummary?: string;
}): Promise<FieldStatusResponse> {
  return postJson<FieldStatusResponse>("/api/servicenow/save-field-status", {
    ticket_number: args.ticketNumber,
    ticket_type: args.ticketType,
    field_name: args.fieldName,
    status: args.status,
    final_value: args.finalValue,
    source: args.source,
    ticket_summary: args.ticketSummary
  });
}
