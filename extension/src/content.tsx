import React, { useEffect, useMemo, useRef, useState } from "react";
import { createRoot, type Root } from "react-dom/client";
import {
  AlertCircle,
  Check,
  Eraser,
  FilePlus2,
  Loader2,
  MessageCirclePlus,
  Minimize2,
  NotebookPen,
  RefreshCw,
  Undo2,
  Wand2
} from "lucide-react";

import { generateField, generateFields, reviseField, saveFieldStatus } from "./api";
import {
  attachManualEditDetector,
  ensureInlineMount,
  hasSupportedFieldElements,
  readFieldValue,
  readTicketContext,
  setFieldValue,
  SUPPORTED_FIELDS
} from "./servicenow/fieldAdapter";
import type { FieldStatus, GeneratedFieldsResponse, SupportedFieldName, TicketContext } from "./types";
import aiBotUrl from "./images/AI Bot.png";
import "./styles.css";

const inlineRoots = new Map<SupportedFieldName, Root>();
const PANEL_STORAGE_KEY = "edson-ai-panel-position";
const PANEL_WIDTH = 520;
const PANEL_MARGIN = 16;
const BOT_IMAGE_URL = getExtensionAssetUrl(aiBotUrl);

interface PanelPosition {
  left: number;
  top: number;
}

interface AssistantAction {
  id: string;
  label: string;
  tone: "blue" | "purple" | "primary" | "mint" | "orange";
  icon: React.ComponentType<{ className?: string }>;
  fields: SupportedFieldName[];
}

function AssistantPanel() {
  const [activeAction, setActiveAction] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [lastContext, setLastContext] = useState<TicketContext | null>(null);
  const [nextResponseContext, setNextResponseContext] = useState("");
  const [position, setPosition] = useState<PanelPosition>(() => getInitialPanelPosition());
  const dragState = useRef<{ offsetX: number; offsetY: number } | null>(null);
  const [statuses, setStatuses] = useState<Record<SupportedFieldName, FieldStatus>>({
    short_description: "Ready",
    description: "Ready",
    additional_comments: "Ready",
    work_notes: "Ready"
  });

  const completedCount = useMemo(
    () => Object.values(statuses).filter((status) => status === "Accepted").length,
    [statuses]
  );

  useEffect(() => {
    const handlePointerMove = (event: PointerEvent) => {
      if (!dragState.current) {
        return;
      }
      const nextPosition = clampPanelPosition({
        left: event.clientX - dragState.current.offsetX,
        top: event.clientY - dragState.current.offsetY
      });
      setPosition(nextPosition);
    };

    const handlePointerUp = () => {
      if (!dragState.current) {
        return;
      }
      dragState.current = null;
      window.localStorage.setItem(PANEL_STORAGE_KEY, JSON.stringify(position));
    };

    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    return () => {
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
    };
  }, [position]);

  useEffect(() => {
    window.localStorage.setItem(PANEL_STORAGE_KEY, JSON.stringify(position));
  }, [position]);

  function handleDragStart(event: React.PointerEvent<HTMLDivElement>) {
    dragState.current = {
      offsetX: event.clientX - position.left,
      offsetY: event.clientY - position.top
    };
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  async function handleGenerate(targetFields: SupportedFieldName[] = SUPPORTED_FIELDS, actionId = "generate") {
    setActiveAction(actionId);
    setError("");

    try {
      const ticketContext = readTicketContext();
      const previousValues = readCurrentFieldValues(targetFields);
      const userInstruction = buildGenerationInstruction(targetFields, nextResponseContext);
      const response =
        targetFields.length === 1
          ? await generateField(ticketContext, targetFields[0], userInstruction)
          : await generateFields(ticketContext, userInstruction);
      const fillResults = fillFieldsFromResponse(response, targetFields);
      setLastContext(ticketContext);
      if (nextResponseContext.trim() && userInstruction) {
        setNextResponseContext("");
      }

      setStatuses((current) => {
        const nextStatuses = { ...current };
        for (const fieldName of targetFields) {
          const generatedValue = getGeneratedFieldValue(response, fieldName);
          nextStatuses[fieldName] = generatedValue && fillResults[fieldName] ? "AI Generated" : "Error";
        }
        return nextStatuses;
      });
      if (Object.values(fillResults).every((wasFilled) => !wasFilled)) {
        setError("AI generated text, but this frame does not expose the editable ServiceNow fields.");
      }
      renderInlineControls(ticketContext, response, (fieldName, status) => {
        setStatuses((current) => ({ ...current, [fieldName]: status }));
      }, targetFields, previousValues);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to generate fields.");
    } finally {
      setActiveAction(null);
    }
  }

  const actions: AssistantAction[] = [
    {
      id: "short_description",
      label: "Fill Short Description",
      tone: "blue",
      icon: FilePlus2,
      fields: ["short_description"]
    },
    {
      id: "description",
      label: "Fill Description",
      tone: "purple",
      icon: FilePlus2,
      fields: ["description"]
    },
    {
      id: "generate",
      label: "Generate All",
      tone: "primary",
      icon: Wand2,
      fields: SUPPORTED_FIELDS
    },
    {
      id: "additional_comments",
      label: "Draft Reply",
      tone: "mint",
      icon: MessageCirclePlus,
      fields: ["additional_comments"]
    },
    {
      id: "work_notes",
      label: "Draft Work Note",
      tone: "orange",
      icon: NotebookPen,
      fields: ["work_notes"]
    }
  ];

  if (isCollapsed) {
    return (
      <button
        type="button"
        className="edson-ai-collapsed-button"
        aria-label="Open Edson AI assistant"
        title="Open Edson AI"
        style={{ left: position.left, top: position.top }}
        onClick={() => setIsCollapsed(false)}
      >
        <img src={BOT_IMAGE_URL} alt="" className="edson-ai-collapsed-image" />
      </button>
    );
  }

  return (
    <section
      className="edson-ai-panel"
      aria-label="ServiceNow AI Ticket Assistant"
      style={{ left: position.left, top: position.top }}
    >
      <div className="edson-ai-hero" onPointerDown={handleDragStart} title="Drag panel">
        <div className="edson-ai-hero-top">
          <div className="edson-ai-brand">Edson AI</div>
          <div className="edson-ai-hero-actions">
            <div className="edson-ai-ticket-chip">{lastContext?.number || "ServiceNow ticket"}</div>
            <button
              type="button"
              className="edson-ai-panel-toggle"
              aria-label="Collapse Edson AI assistant"
              title="Collapse"
              onPointerDown={(event) => event.stopPropagation()}
              onClick={() => setIsCollapsed(true)}
            >
              <Minimize2 className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <div className="edson-ai-bot-stage">
          <div className="edson-ai-orbit" aria-hidden="true" />
          <div className="edson-ai-bot-ring">
            <img src={BOT_IMAGE_URL} alt="AI assistant robot" className="edson-ai-bot-image" />
          </div>
        </div>

        <h2 className="edson-ai-title">AI Ticket Assistant</h2>
        <p className="edson-ai-subtitle">Let AI help you complete your ServiceNow ticket faster and more accurately.</p>
      </div>

      <div className="edson-ai-action-area">
        <div className="edson-ai-action-grid">
          {actions.map((action) => (
            <ActionTile
              key={action.id}
              action={action}
              activeAction={activeAction}
              status={getActionStatus(action, statuses)}
              onClick={() => handleGenerate(action.fields, action.id)}
            />
          ))}
        </div>

        <div className="edson-ai-guidance-panel">
          <div className="edson-ai-guidance-header">
            <span>Next reply guidance</span>
            <button
              type="button"
              className="edson-ai-guidance-clear"
              onClick={() => setNextResponseContext("")}
              disabled={!nextResponseContext.trim() || Boolean(activeAction)}
              title="Clear guidance"
              aria-label="Clear guidance"
            >
              <Eraser className="h-3.5 w-3.5" />
            </button>
          </div>
          <textarea
            className="edson-ai-guidance-input"
            value={nextResponseContext}
            onChange={(event) => setNextResponseContext(event.target.value)}
            placeholder="Example: approve keeping the charger until Aug 4 and ask for an email when back onsite"
            aria-label="Guidance for additional comments or work notes"
            disabled={Boolean(activeAction)}
          />
        </div>

        {error ? (
          <div className="mt-4 flex items-start gap-2 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-800">
            <AlertCircle className="mt-0.5 h-4 w-4 flex-none" />
            <span>{error}</span>
          </div>
        ) : null}

        {completedCount > 0 ? (
          <div className="mt-4 rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-xs font-medium text-emerald-800">
            {completedCount} accepted
          </div>
        ) : null}
      </div>
    </section>
  );
}

function buildGenerationInstruction(fields: SupportedFieldName[], nextResponseContext: string): string | undefined {
  const context = nextResponseContext.trim();
  if (!context) {
    return undefined;
  }
  const targetsConversationField = fields.includes("additional_comments") || fields.includes("work_notes");
  if (!targetsConversationField) {
    return undefined;
  }
  const targetText =
    fields.length === 1
      ? ""
      : "Generate all fields. Apply the following user guidance only to additional_comments and work_notes.";
  return [targetText, `User guidance for the next response/note: ${context}`].filter(Boolean).join("\n\n");
}

function getInitialPanelPosition(): PanelPosition {
  const fallback = getDefaultPanelPosition();
  const stored = window.localStorage.getItem(PANEL_STORAGE_KEY);
  if (!stored) {
    return clampPanelPosition(fallback);
  }
  try {
    const parsed = JSON.parse(stored) as Partial<PanelPosition>;
    if (typeof parsed.left === "number" && typeof parsed.top === "number") {
      return clampPanelPosition({ left: parsed.left, top: parsed.top });
    }
  } catch {
    return clampPanelPosition(fallback);
  }
  return clampPanelPosition(fallback);
}

function getExtensionAssetUrl(assetPath: string): string {
  const normalizedPath = assetPath.replace(/^\//, "");
  if (typeof chrome !== "undefined" && chrome.runtime?.getURL) {
    return chrome.runtime.getURL(normalizedPath);
  }
  return assetPath;
}

function getDefaultPanelPosition(): PanelPosition {
  return {
    left: Math.max(PANEL_MARGIN, window.innerWidth - PANEL_WIDTH - PANEL_MARGIN),
    top: 72
  };
}

function clampPanelPosition(position: PanelPosition): PanelPosition {
  const maxLeft = Math.max(PANEL_MARGIN, window.innerWidth - PANEL_WIDTH - PANEL_MARGIN);
  const maxTop = Math.max(PANEL_MARGIN, window.innerHeight - 120);
  return {
    left: Math.min(Math.max(PANEL_MARGIN, position.left), maxLeft),
    top: Math.min(Math.max(PANEL_MARGIN, position.top), maxTop)
  };
}

function ActionTile(props: {
  action: AssistantAction;
  activeAction: string | null;
  status: FieldStatus;
  onClick: () => void;
}) {
  const Icon = props.action.icon;
  const isActive = props.activeAction === props.action.id;
  const isDisabled = Boolean(props.activeAction);

  return (
    <button
      type="button"
      className={`edson-ai-action-tile edson-ai-action-${props.action.tone}`}
      onClick={props.onClick}
      disabled={isDisabled}
      title={props.action.label}
    >
      <span className="edson-ai-action-icon">
        {isActive ? <Loader2 className="h-5 w-5 animate-spin" /> : <Icon className="h-5 w-5" />}
      </span>
      <span className="edson-ai-action-label">{props.action.label}</span>
    </button>
  );
}

function fillFieldsFromResponse(
  response: GeneratedFieldsResponse,
  fields: SupportedFieldName[]
): Record<SupportedFieldName, boolean> {
  const fillResults: Record<SupportedFieldName, boolean> = {
    short_description: false,
    description: false,
    additional_comments: false,
    work_notes: false
  };

  for (const fieldName of fields) {
    fillResults[fieldName] = setFieldValue(fieldName, getGeneratedFieldValue(response, fieldName));
  }
  return fillResults;
}

function readCurrentFieldValues(fields: SupportedFieldName[]): Record<SupportedFieldName, string> {
  const values: Record<SupportedFieldName, string> = {
    short_description: "",
    description: "",
    additional_comments: "",
    work_notes: ""
  };

  for (const fieldName of fields) {
    values[fieldName] = readFieldValue(fieldName);
  }
  return values;
}

function getGeneratedFieldValue(response: GeneratedFieldsResponse, fieldName: SupportedFieldName): string {
  return response[fieldName];
}

function getActionStatus(action: AssistantAction, statuses: Record<SupportedFieldName, FieldStatus>): FieldStatus {
  if (action.fields.length === 1) {
    return statuses[action.fields[0]];
  }
  if (action.fields.every((fieldName) => statuses[fieldName] === "AI Generated" || statuses[fieldName] === "AI Revised")) {
    return "AI Generated";
  }
  if (action.fields.some((fieldName) => statuses[fieldName] === "Error")) {
    return "Error";
  }
  if (action.fields.some((fieldName) => statuses[fieldName] === "Reverted")) {
    return "Reverted";
  }
  return "Ready";
}

function InlineFieldControl(props: {
  fieldName: SupportedFieldName;
  ticketContext: TicketContext;
  initialValue: string;
  previousValue: string;
  onStatusChange: (fieldName: SupportedFieldName, status: FieldStatus) => void;
}) {
  const [moreContext, setMoreContext] = useState("");
  const [status, setStatus] = useState<FieldStatus>("AI Generated");
  const [isRevising, setIsRevising] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");
  const lastAiValue = useRef(props.initialValue);

  useEffect(() => {
    lastAiValue.current = props.initialValue;
  }, [props.initialValue]);

  useEffect(() => {
    return attachManualEditDetector(
      props.fieldName,
      () => lastAiValue.current,
      () => {
        setStatus("Manual Edit Detected");
        props.onStatusChange(props.fieldName, "Manual Edit Detected");
      }
    );
  }, [props]);

  async function handleRevise() {
    if (!moreContext.trim()) {
      setError("Add revision context first.");
      return;
    }

    setIsRevising(true);
    setError("");
    try {
      const currentValue = readFieldValue(props.fieldName);
      const response = await reviseField({
        ticketNumber: props.ticketContext.number,
        fieldName: props.fieldName,
        currentFieldValue: currentValue,
        revisionInstruction: moreContext,
        ticketContext: readTicketContext()
      });
      lastAiValue.current = response.revised_value;
      setFieldValue(props.fieldName, response.revised_value);
      setStatus("AI Revised");
      props.onStatusChange(props.fieldName, "AI Revised");
      setMoreContext("");
    } catch (caught) {
      setStatus("Error");
      props.onStatusChange(props.fieldName, "Error");
      setError(caught instanceof Error ? caught.message : "Unable to revise field.");
    } finally {
      setIsRevising(false);
    }
  }

  function handleRevert() {
    setError("");
    lastAiValue.current = props.previousValue;
    setFieldValue(props.fieldName, props.previousValue);
    setStatus("Reverted");
    props.onStatusChange(props.fieldName, "Reverted");
  }

  async function handleAccept() {
    setIsSaving(true);
    setError("");
    try {
      await saveFieldStatus({
        ticketNumber: props.ticketContext.number,
        ticketType: props.ticketContext.ticket_type,
        fieldName: props.fieldName,
        status: "accepted",
        finalValue: readFieldValue(props.fieldName),
        source:
          status === "AI Revised"
            ? "ai_revised"
            : status === "Manual Edit Detected" || status === "Reverted"
              ? "manual"
              : "ai_generated",
        ticketSummary: buildTicketSummary(props.ticketContext)
      });
      setStatus("Accepted");
      props.onStatusChange(props.fieldName, "Accepted");
    } catch (caught) {
      setStatus("Error");
      props.onStatusChange(props.fieldName, "Error");
      setError(caught instanceof Error ? caught.message : "Unable to save status.");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="rounded-lg border border-slate-300 bg-white p-2 shadow-sm">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs font-semibold text-slate-800">{fieldLabel(props.fieldName)}</div>
        <StatusPill status={status} />
      </div>
      <div className="flex min-w-0 flex-wrap items-center gap-2">
        <input
          className="edson-ai-input flex min-w-[180px] flex-1"
          value={moreContext}
          onChange={(event) => setMoreContext(event.target.value)}
          placeholder="Revision guidance"
        />
        <button
          type="button"
          className="edson-ai-icon-button"
          onClick={handleRevert}
          disabled={isRevising || isSaving}
          title="Revert to previous content"
        >
          <Undo2 className="h-4 w-4" />
        </button>
        <button
          type="button"
          className="edson-ai-icon-button"
          onClick={handleRevise}
          disabled={isRevising || isSaving}
          title="Revise"
        >
          {isRevising ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
        </button>
        <button
          type="button"
          className="edson-ai-icon-button"
          onClick={handleAccept}
          disabled={isRevising || isSaving}
          title="OK"
        >
          {isSaving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
        </button>
      </div>
      {error ? <div className="mt-2 text-xs text-red-700">{error}</div> : null}
    </div>
  );
}

function StatusPill({ status }: { status: FieldStatus }) {
  const classes: Record<FieldStatus, string> = {
    Ready: "bg-slate-100 text-slate-600",
    Generating: "bg-indigo-50 text-indigo-800",
    "AI Generated": "bg-blue-50 text-blue-800",
    "AI Revised": "bg-violet-50 text-violet-800",
    Reverted: "bg-slate-100 text-slate-800",
    Accepted: "bg-emerald-50 text-emerald-800",
    "Manual Edit Detected": "bg-amber-50 text-amber-800",
    Error: "bg-red-50 text-red-800"
  };

  return <span className={`edson-ai-status ${classes[status]}`}>{status}</span>;
}

function renderInlineControls(
  ticketContext: TicketContext,
  response: GeneratedFieldsResponse,
  onStatusChange: (fieldName: SupportedFieldName, status: FieldStatus) => void,
  fields: SupportedFieldName[] = SUPPORTED_FIELDS,
  previousValues?: Record<SupportedFieldName, string>
) {
  const values: Record<SupportedFieldName, string> = {
    short_description: response.short_description,
    description: response.description,
    additional_comments: response.additional_comments,
    work_notes: response.work_notes
  };

  for (const fieldName of fields) {
    const mount = ensureInlineMount(fieldName);
    if (!mount) {
      continue;
    }

    const existingRoot = inlineRoots.get(fieldName);
    const root = existingRoot ?? createRoot(mount);
    inlineRoots.set(fieldName, root);
    root.render(
      <InlineFieldControl
        fieldName={fieldName}
        ticketContext={ticketContext}
        initialValue={values[fieldName]}
        previousValue={previousValues?.[fieldName] ?? ""}
        onStatusChange={onStatusChange}
      />
    );
  }
}

function buildTicketSummary(ticketContext: TicketContext): string {
  return [ticketContext.number, ticketContext.item, ticketContext.additional_details].filter(Boolean).join(" | ");
}

function fieldLabel(fieldName: SupportedFieldName): string {
  const labels: Record<SupportedFieldName, string> = {
    short_description: "Short description",
    description: "Description",
    additional_comments: "Additional comments",
    work_notes: "Work notes"
  };
  return labels[fieldName];
}

function mountPanel() {
  if (document.getElementById("edson-ai-panel-root")) {
    return;
  }
  if (!hasSupportedFieldElements()) {
    return;
  }

  const rootElement = document.createElement("div");
  rootElement.id = "edson-ai-panel-root";
  document.body.appendChild(rootElement);
  createRoot(rootElement).render(<AssistantPanel />);
}

function mountWhenFormIsReady() {
  let attempts = 0;
  const maxAttempts = 40;

  const tryMount = () => {
    attempts += 1;
    mountPanel();
    if (document.getElementById("edson-ai-panel-root") || attempts >= maxAttempts) {
      window.clearInterval(intervalId);
    }
  };

  const intervalId = window.setInterval(tryMount, 500);
  tryMount();
}

mountWhenFormIsReady();
