import type { GeneratedFieldsResponse, SupportedFieldName, TicketContext } from "../types";

type FieldElement = HTMLInputElement | HTMLTextAreaElement | HTMLElement;

interface ActivityEntry {
  type: string;
  author: string;
  timestamp: string;
  text: string;
  display_order: number;
}

const FIELD_SELECTORS: Record<SupportedFieldName, string[]> = {
  short_description: [
    'input[name="short_description"]',
    'textarea[name="short_description"]',
    'input[name$=".short_description"]',
    'textarea[name$=".short_description"]',
    'input[id$=".short_description"]',
    'textarea[id$=".short_description"]',
    'input[id="incident.short_description"]',
    'input[id="sc_task.short_description"]',
    'input[aria-label*="Short description" i]',
    'textarea[aria-label*="Short description" i]'
  ],
  description: [
    'textarea[name="description"]',
    'textarea[name$=".description"]',
    'textarea[id$=".description"]',
    'textarea[id="incident.description"]',
    'textarea[id="sc_task.description"]',
    'textarea[aria-label="Description" i]',
    'textarea[aria-label*="Description" i]'
  ],
  additional_comments: [
    'textarea[name="comments"]',
    'textarea[name="additional_comments"]',
    'textarea[name$=".comments"]',
    'textarea[name$=".additional_comments"]',
    'textarea[aria-label*="Additional comments" i]',
    'textarea[placeholder*="Additional comments" i]',
    'textarea[aria-label*="Comments" i]',
    'textarea[placeholder*="Comments" i]',
    'textarea[name="activity-stream-comments-textarea"]',
    'textarea[id="activity-stream-comments-textarea"]',
    'textarea[id$=".comments"]',
    'textarea[id$=".additional_comments"]',
    'textarea[id*="comments" i]',
    '[contenteditable="true"][aria-label*="Additional comments" i]',
    '[contenteditable="true"][aria-label*="Comments" i]'
  ],
  work_notes: [
    'textarea[name="work_notes"]',
    'textarea[name$=".work_notes"]',
    'textarea[aria-label*="Work notes" i]',
    'textarea[placeholder*="Work notes" i]',
    'textarea[name="activity-stream-work_notes-textarea"]',
    'textarea[id="activity-stream-work_notes-textarea"]',
    'textarea[id$=".work_notes"]',
    'textarea[id*="work_notes" i]',
    '[contenteditable="true"][aria-label*="Work notes" i]'
  ]
};

const CONTEXT_SELECTORS: Record<string, string[]> = {
  number: ['input[name="number"]', 'input[id$=".number"]', '[data-test-id="ticket-number"]'],
  requested_for: [
    'input[name^="sys_display."][name$=".requested_for"]',
    'input[id^="sys_display."][id$=".requested_for"]',
    'input[name="sys_display.sc_task.requested_for"]',
    'input[id="sys_display.sc_task.requested_for"]',
    'input[name="requested_for"]',
    'input[id$=".requested_for"]',
    'input[aria-label*="Requested for" i]'
  ],
  location: [
    'input[name^="sys_display."][name$=".location"]',
    'input[id^="sys_display."][id$=".location"]',
    'input[name="location"]',
    'input[id$=".location"]',
    'input[aria-label*="Location" i]'
  ],
  campus: [
    'input[name^="sys_display."][name$=".campus"]',
    'input[id^="sys_display."][id$=".campus"]',
    'input[name="campus"]',
    'input[id$=".campus"]',
    'input[aria-label*="Campus" i]'
  ],
  building: [
    'input[name^="sys_display."][name$=".building"]',
    'input[id^="sys_display."][id$=".building"]',
    'input[name="building"]',
    'input[id$=".building"]',
    'input[aria-label*="Building" i]'
  ],
  room: [
    'input[name^="sys_display."][name$=".room"]',
    'input[id^="sys_display."][id$=".room"]',
    'input[name="room"]',
    'input[id$=".room"]',
    'input[aria-label*="Room" i]'
  ],
  room_number: [
    'input[name="room_number"]',
    'input[name$=".room_number"]',
    'input[id$=".room_number"]',
    'input[aria-label*="Room Number" i]',
    'input[aria-label*="Room" i]'
  ],
  item: [
    'input[name^="sys_display."][name$=".cat_item"]',
    'input[id^="sys_display."][id$=".cat_item"]',
    'input[name^="sys_display."][name$=".item"]',
    'input[id^="sys_display."][id$=".item"]',
    'input[name="cat_item"]',
    'input[id$=".cat_item"]',
    'input[aria-label*="Item" i]'
  ],
  additional_details: [
    'textarea[name="additional_details"]',
    'textarea[name$=".additional_details"]',
    'textarea[id$=".additional_details"]',
    'textarea[aria-label*="Additional details" i]',
    'textarea[aria-label*="Details" i]'
  ],
  more_information: [
    'textarea[name="more_information"]',
    'textarea[name$=".more_information"]',
    'textarea[id$=".more_information"]',
    'textarea[aria-label*="More information" i]',
    'textarea[aria-label*="More info" i]'
  ]
};

export const SUPPORTED_FIELDS: SupportedFieldName[] = [
  "short_description",
  "description",
  "additional_comments",
  "work_notes"
];

export function hasSupportedFieldElements(): boolean {
  return SUPPORTED_FIELDS.some((fieldName) => Boolean(findFieldElement(fieldName)));
}

export function findFieldElement(fieldName: SupportedFieldName): FieldElement | null {
  return (
    findBySelectors(FIELD_SELECTORS[fieldName]) ??
    findByLabel(fieldNameToLabel(fieldName)) ??
    findByNearbyFieldText(fieldName)
  );
}

export function readFieldValue(fieldName: SupportedFieldName): string {
  const element = findFieldElement(fieldName);
  return element ? readElementValue(element) : "";
}

export function setFieldValue(fieldName: SupportedFieldName, value: string): boolean {
  let element = findFieldElement(fieldName);
  if (isJournalField(fieldName) && (!element || !isVisibleElement(element))) {
    const previousElement = element;
    activateJournalTab(fieldName);
    element = findFieldElement(fieldName);
    if (element && !isVisibleElement(element) && previousElement) {
      element = previousElement;
    }
  }
  if (!element) {
    return false;
  }
  setElementValue(element, value);
  return true;
}

export function fillGeneratedFields(response: GeneratedFieldsResponse): Record<SupportedFieldName, boolean> {
  return {
    short_description: setFieldValue("short_description", response.short_description),
    description: setFieldValue("description", response.description),
    additional_comments: setFieldValue("additional_comments", response.additional_comments),
    work_notes: setFieldValue("work_notes", response.work_notes)
  };
}

export function readTicketContext(): TicketContext {
  const moreInformation =
    readContextValue("more_information") ||
    readByLabelText("More information") ||
    readBestMoreInformationText() ||
    readContextValue("additional_details") ||
    readByLabelText("Additional details") ||
    readByLabelText("Request details");
  const campus = readContextValue("campus") || readByLabelText("Campus");
  const building = readContextValue("building") || readByLabelText("Building");
  const roomNumber =
    readContextValue("room_number") ||
    readByLabelText("Room Number") ||
    readContextValue("room") ||
    readByLabelText("Room");

  return {
    ticket_type: inferTicketType(),
    number: readContextValue("number") || inferTicketNumberFromPage(),
    requested_for:
      readContextValue("requested_for") ||
      readByLabelText("Requested for") ||
      inferPersonNameFromDetails(moreInformation),
    campus,
    building,
    room_number: roomNumber,
    location: readContextValue("location") || readByLabelText("Location") || campus,
    room: roomNumber,
    item: readContextValue("item") || readByLabelText("Item") || inferItemFromDetails(moreInformation),
    more_information: moreInformation,
    recent_activity: readRecentActivitySummary(),
    additional_details: moreInformation,
    current_short_description: readFieldValue("short_description"),
    current_description: readFieldValue("description"),
    current_additional_comments: readFieldValue("additional_comments"),
    current_work_notes: readFieldValue("work_notes")
  };
}

function readRecentActivitySummary(): string {
  const structuredEntries = readStructuredRecentActivity();
  if (structuredEntries.length > 0) {
    return JSON.stringify({
      format: "servicenow_activity_v1",
      order: "visible_newest_first",
      entries: structuredEntries
    });
  }

  const selectors = [
    "#activity-stream",
    ".activity-stream",
    "[id*='activity'][id*='stream' i]",
    "[aria-label*='Activities' i]",
    "[aria-label*='Activity' i]"
  ];
  for (const selector of selectors) {
    const element = document.querySelector<HTMLElement>(selector);
    const text = element?.innerText?.trim();
    if (text) {
      return text.slice(-4000);
    }
  }
  return "";
}

function readStructuredRecentActivity(): ActivityEntry[] {
  const stream = findActivityStreamElement();
  if (!stream) {
    return [];
  }

  const candidates = findActivityEntryElements(stream);
  const entries = candidates
    .map((element, index) => parseActivityEntry(element, index))
    .filter((entry): entry is ActivityEntry => Boolean(entry));

  return dedupeActivityEntries(entries).slice(0, 12);
}

function findActivityStreamElement(): HTMLElement | null {
  const selectors = [
    "#activity-stream",
    ".activity-stream",
    "[id*='activity'][id*='stream' i]",
    "[aria-label*='Activities' i]",
    "[aria-label*='Activity' i]"
  ];
  for (const selector of selectors) {
    const element = document.querySelector<HTMLElement>(selector);
    if (element?.innerText?.trim()) {
      return element;
    }
  }
  return null;
}

function findActivityEntryElements(stream: HTMLElement): HTMLElement[] {
  const selectors = [
    "[class*='activity-stream-entry' i]",
    "[class*='activity-stream-card' i]",
    "[class*='activity-card' i]",
    "[class*='sn-card' i]",
    "[role='article']",
    "li"
  ];
  const bySelector = selectors.flatMap((selector) => Array.from(stream.querySelectorAll<HTMLElement>(selector)));
  const unique = Array.from(new Set(bySelector));
  const useful = unique.filter((element) => isLikelyActivityEntry(element));
  if (useful.length > 0) {
    return useful;
  }
  return Array.from(stream.children).filter((element): element is HTMLElement => {
    return element instanceof HTMLElement && isLikelyActivityEntry(element);
  });
}

function isLikelyActivityEntry(element: HTMLElement): boolean {
  const text = normalizeWhitespace(element.innerText || element.textContent || "");
  if (text.length < 20 || text.length > 5000) {
    return false;
  }
  return /(additional comments|work notes|email sent|comments added|incident|task|20\d{2}-\d{2}-\d{2})/i.test(text);
}

function parseActivityEntry(element: HTMLElement, displayOrder: number): ActivityEntry | null {
  const rawText = normalizeWhitespace(element.innerText || element.textContent || "");
  if (!rawText) {
    return null;
  }

  const type = inferActivityEntryType(rawText);
  const timestamp = rawText.match(/\b20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\b/)?.[0] ?? "";
  const author = inferActivityAuthor(rawText);
  const text = cleanActivityBody(rawText, type, author);

  if (!text || (type === "email_sent" && text.length < 40)) {
    return null;
  }

  return {
    type,
    author,
    timestamp,
    text: text.slice(0, 1200),
    display_order: displayOrder
  };
}

function inferActivityEntryType(text: string): string {
  if (/work notes/i.test(text)) {
    return "work_notes";
  }
  if (/additional comments|comments added/i.test(text)) {
    return "additional_comments";
  }
  if (/email sent/i.test(text)) {
    return "email_sent";
  }
  return "activity";
}

function inferActivityAuthor(text: string): string {
  const withoutInitials = text.replace(/^[A-Z]{1,3}\s+/, "");
  const beforeType = withoutInitials.split(/\b(?:Additional comments|Work notes|Email sent)\b/i)[0]?.trim();
  if (beforeType && beforeType.length <= 80 && !/^system$/i.test(beforeType)) {
    return beforeType;
  }
  if (/^system\b/i.test(withoutInitials)) {
    return "System";
  }
  return "";
}

function cleanActivityBody(text: string, type: string, author: string): string {
  let cleaned = text
    .replace(/\b(?:Additional comments|Work notes|Email sent)\s*[\u2022-]?\s*20\d{2}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}/gi, " ")
    .replace(/\bShow email details\b/gi, " ")
    .replace(/\bSubject:\s*.*?(?=\bFrom:\b|\bTo:\b|$)/i, " ")
    .replace(/\bFrom:\s*\S+/gi, " ")
    .replace(/\bTo:\s*\S+/gi, " ")
    .replace(/^[A-Z]{1,3}\s+/, " ")
    .replace(/^System\s+/i, " ");

  if (author) {
    cleaned = cleaned.replace(new RegExp(`^${escapeRegExp(author)}\\s+`, "i"), " ");
  }

  if (type === "email_sent") {
    cleaned = cleaned.replace(/\bEmail sent\b/gi, " ");
  }

  return normalizeWhitespace(cleaned);
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function dedupeActivityEntries(entries: ActivityEntry[]): ActivityEntry[] {
  const seen = new Set<string>();
  const deduped: ActivityEntry[] = [];
  for (const entry of entries) {
    const key = `${entry.type}|${entry.timestamp}|${entry.text.slice(0, 160)}`;
    if (seen.has(key)) {
      continue;
    }
    seen.add(key);
    deduped.push(entry);
  }
  return deduped;
}

function normalizeWhitespace(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

export function ensureInlineMount(fieldName: SupportedFieldName): HTMLElement | null {
  const field = findFieldElement(fieldName);
  if (!field) {
    return null;
  }

  const mountId = `edson-ai-inline-${fieldName}`;
  let mount = document.getElementById(mountId);
  if (mount) {
    return mount;
  }

  mount = document.createElement("div");
  mount.id = mountId;
  mount.className = "edson-ai-inline-mount";

  const container = field.closest(".form-group, .form-field, tr, td, div") ?? field.parentElement;
  if (container && container.parentElement) {
    container.insertAdjacentElement("afterend", mount);
  } else {
    field.insertAdjacentElement("afterend", mount);
  }
  return mount;
}

export function attachManualEditDetector(
  fieldName: SupportedFieldName,
  getLastAiValue: () => string,
  onManualEdit: () => void
): () => void {
  const element = findFieldElement(fieldName);
  if (!element) {
    return () => undefined;
  }

  const handler = () => {
    const current = readElementValue(element);
    const lastAiValue = getLastAiValue();
    if (lastAiValue && current !== lastAiValue) {
      onManualEdit();
    }
  };

  element.addEventListener("input", handler);
  element.addEventListener("change", handler);
  return () => {
    element.removeEventListener("input", handler);
    element.removeEventListener("change", handler);
  };
}

function readContextValue(key: keyof typeof CONTEXT_SELECTORS): string {
  const element = findMeaningfulBySelectors(CONTEXT_SELECTORS[key]);
  return element ? sanitizeContextValue(readElementValue(element)) : "";
}

function findBySelectors(selectors: string[]): FieldElement | null {
  let fallback: FieldElement | null = null;
  for (const selector of selectors) {
    const foundElements = Array.from(document.querySelectorAll<FieldElement>(selector));
    for (const found of foundElements) {
      if (!isWritableCandidate(found)) {
        continue;
      }
      if (isVisibleElement(found)) {
        return found;
      }
      fallback ??= found;
    }
  }
  return fallback;
}

function findMeaningfulBySelectors(selectors: string[]): FieldElement | null {
  let firstVisible: FieldElement | null = null;

  for (const selector of selectors) {
    const foundElements = Array.from(document.querySelectorAll<FieldElement>(selector));
    for (const found of foundElements) {
      if (!firstVisible && isVisibleElement(found)) {
        firstVisible = found;
      }
      const value = sanitizeContextValue(readElementValue(found));
      if (value && isVisibleElement(found)) {
        return found;
      }
    }
  }

  if (firstVisible && sanitizeContextValue(readElementValue(firstVisible))) {
    return firstVisible;
  }
  return null;
}

function findByLabel(labelText: string): FieldElement | null {
  const labels = Array.from(document.querySelectorAll("label"));
  for (const label of labels) {
    if (!label.textContent?.toLowerCase().includes(labelText.toLowerCase())) {
      continue;
    }
    if (label.htmlFor) {
      const byFor = document.getElementById(label.htmlFor);
      if (byFor) {
        return byFor;
      }
    }
    const wrapper = label.closest(".form-group, .form-field, tr, div");
    const inputs = Array.from(wrapper?.querySelectorAll<FieldElement>("textarea, input, [contenteditable='true']") ?? []);
    const visibleInput = inputs.find((input) => isWritableCandidate(input) && isVisibleElement(input));
    if (visibleInput) {
      return visibleInput;
    }
    const fallbackInput = inputs.find(isWritableCandidate);
    if (fallbackInput) {
      return fallbackInput;
    }
  }
  return null;
}

function findByNearbyFieldText(fieldName: SupportedFieldName): FieldElement | null {
  const labelText = fieldNameToLabel(fieldName).toLowerCase();
  const looseText = fieldName === "additional_comments" ? "comments" : labelText;
  const candidates = Array.from(document.querySelectorAll<FieldElement>("textarea, input, [contenteditable='true']"))
    .filter(isWritableCandidate)
    .map((element) => {
      const text = `${getElementFieldText(element)}\n${getSurroundingText(element)}`.toLowerCase();
      let score = 0;
      if (text.includes(labelText)) score += 1000;
      if (text.includes(looseText)) score += 250;
      if (isVisibleElement(element)) score += 500;
      if (element instanceof HTMLTextAreaElement) score += 100;
      return { element, score };
    })
    .filter((candidate) => candidate.score >= 1000)
    .sort((left, right) => right.score - left.score);

  return candidates[0]?.element ?? null;
}

function readByLabelText(labelText: string): string {
  const element = findByLabel(labelText);
  return element ? sanitizeContextValue(readElementValue(element)) : "";
}

function readBestMoreInformationText(): string {
  const outputFields = new Set<Element>(
    SUPPORTED_FIELDS.map((fieldName) => findFieldElement(fieldName)).filter((element): element is FieldElement =>
      Boolean(element)
    )
  );

  const candidates = Array.from(document.querySelectorAll<HTMLTextAreaElement>("textarea"))
    .filter((textarea) => isVisibleElement(textarea))
    .filter((textarea) => !outputFields.has(textarea))
    .map((textarea) => {
      const value = sanitizeContextValue(textarea.value);
      const surroundingText = getSurroundingText(textarea).toLowerCase();
      return {
        value,
        score: scoreMoreInformationCandidate(value, surroundingText)
      };
    })
    .filter((candidate) => candidate.value.length >= 30)
    .sort((left, right) => right.score - left.score);

  return candidates[0]?.value ?? "";
}

function scoreMoreInformationCandidate(value: string, surroundingText: string): number {
  const lowered = value.toLowerCase();
  let score = value.length;

  if (surroundingText.includes("more information")) score += 1000;
  if (surroundingText.includes("details")) score += 150;
  if (lowered.includes("bios")) score += 250;
  if (lowered.includes("thermal")) score += 250;
  if (lowered.includes("shutting")) score += 200;
  if (lowered.includes("restart")) score += 125;
  if (lowered.includes("blocked")) score += 75;
  if (isLikelyRequestMetadata(value)) score -= 2000;

  return score;
}

function getSurroundingText(element: Element): string {
  const container =
    element.closest(".form-group, .form-field, .variable, .question, .sn-form-field, tr, div") ?? element.parentElement;
  const previous = container?.previousElementSibling?.textContent ?? "";
  const current = container?.textContent ?? "";
  const parent = container?.parentElement?.textContent ?? "";
  return `${previous}\n${current}\n${parent}`.slice(0, 2000);
}

function getElementFieldText(element: FieldElement): string {
  const attributes = [
    element.getAttribute("aria-label"),
    element.getAttribute("placeholder"),
    element.getAttribute("name"),
    element.getAttribute("id"),
    element.getAttribute("title")
  ];
  return attributes.filter(Boolean).join("\n");
}

function readElementValue(element: FieldElement): string {
  if (element instanceof HTMLTextAreaElement) {
    return element.value.trim();
  }
  if (element instanceof HTMLInputElement) {
    return (
      element.getAttribute("displayvalue") ||
      element.getAttribute("data-display-value") ||
      element.getAttribute("title") ||
      element.value
    ).trim();
  }
  return (element.textContent ?? "").trim();
}

function setElementValue(element: FieldElement, value: string): void {
  if (element instanceof HTMLInputElement || element instanceof HTMLTextAreaElement) {
    const prototype = element instanceof HTMLTextAreaElement ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
    const valueSetter = Object.getOwnPropertyDescriptor(prototype, "value")?.set;
    valueSetter?.call(element, value);
  } else if (element.isContentEditable) {
    element.textContent = value;
  }

  element.dispatchEvent(new Event("input", { bubbles: true }));
  element.dispatchEvent(new Event("change", { bubbles: true }));
  element.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true }));
}

function isWritableCandidate(element: FieldElement): boolean {
  if (element instanceof HTMLInputElement) {
    return element.type !== "hidden" && !element.disabled && !element.readOnly;
  }
  if (element instanceof HTMLTextAreaElement) {
    return !element.disabled && !element.readOnly;
  }
  return element.isContentEditable;
}

function isJournalField(fieldName: SupportedFieldName): boolean {
  return fieldName === "additional_comments" || fieldName === "work_notes";
}

function activateJournalTab(fieldName: SupportedFieldName): void {
  const targetText = fieldNameToLabel(fieldName).toLowerCase();
  const tabLikeElements = Array.from(
    document.querySelectorAll<HTMLElement>(
      'button, a, [role="tab"], [role="button"], [aria-controls], .tab_caption, .tabs2_tab, .tabs2_tab_inner, .sn-tabs-basic-item'
    )
  );

  const target = tabLikeElements.find((element) => {
    if (!isVisibleElement(element)) {
      return false;
    }
    const text = (element.innerText || element.textContent || "").trim().toLowerCase();
    return text.includes(targetText) && text.length <= 80;
  });

  target?.click();
}

function inferTicketType(): string {
  const path = window.location.pathname.toLowerCase();
  const href = window.location.href.toLowerCase();
  if (path.includes("incident") || href.includes("incident")) {
    return "incident";
  }
  if (path.includes("sc_task") || href.includes("sc_task") || href.includes("catalog")) {
    return "catalog_task";
  }
  if (href.includes("ritm")) {
    return "request_item";
  }
  return "servicenow";
}

function inferTicketNumberFromPage(): string {
  const text = document.body.innerText;
  const match = text.match(/\b(?:INC|TASK|RITM|REQ)\d{5,}\b/);
  return match?.[0] ?? "";
}

function sanitizeContextValue(value: string): string {
  const trimmed = value.trim();
  if (!trimmed || isLikelySysId(trimmed) || isLikelyRequestMetadata(trimmed)) {
    return "";
  }
  return trimmed;
}

function isLikelySysId(value: string): boolean {
  return /^[0-9a-f]{32}$/i.test(value.trim());
}

function isLikelyRequestMetadata(value: string): boolean {
  return /^\s*(?:RITM|REQ|TASK|INC)\d+\s+request\s+for\s+/i.test(value.trim());
}

function isVisibleElement(element: Element): boolean {
  if (element instanceof HTMLInputElement && element.type === "hidden") {
    return false;
  }
  const rect = element.getBoundingClientRect();
  return rect.width > 0 && rect.height > 0;
}

function inferPersonNameFromDetails(details: string): string {
  const parts = details
    .split(/\s+-\s+/)
    .map((part) => part.trim())
    .filter(Boolean);
  const candidate = parts.find((part) => /^[A-Z][A-Za-z'.-]+(?:\s+[A-Z][A-Za-z'.-]+)+$/.test(part));
  return candidate ?? "";
}

function inferItemFromDetails(details: string): string {
  const parts = details
    .split(/\s+-\s+/)
    .map((part) => part.trim())
    .filter(Boolean);
  return parts[0] && !isLikelySysId(parts[0]) ? parts[0] : "";
}

function fieldNameToLabel(fieldName: SupportedFieldName): string {
  const labels: Record<SupportedFieldName, string> = {
    short_description: "Short description",
    description: "Description",
    additional_comments: "Additional comments",
    work_notes: "Work notes"
  };
  return labels[fieldName];
}
