const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "");

interface ApiPostMessage {
  type: "EDSON_API_POST";
  path: string;
  body: unknown;
}

type ApiPostResult =
  | {
      ok: true;
      data: unknown;
    }
  | {
      ok: false;
      error: string;
    };

chrome.runtime.onMessage.addListener((message: unknown, _sender, sendResponse) => {
  if (!isApiPostMessage(message)) {
    return false;
  }

  postJson(message)
    .then((data) => sendResponse({ ok: true, data } satisfies ApiPostResult))
    .catch((error: unknown) => {
      const messageText = error instanceof Error ? error.message : "Backend request failed.";
      sendResponse({ ok: false, error: messageText } satisfies ApiPostResult);
    });

  return true;
});

async function postJson(message: ApiPostMessage): Promise<unknown> {
  const response = await fetch(`${BACKEND_URL}${message.path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(message.body)
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }

  return response.json();
}

function isApiPostMessage(message: unknown): message is ApiPostMessage {
  if (!message || typeof message !== "object") {
    return false;
  }
  const candidate = message as Partial<ApiPostMessage>;
  return candidate.type === "EDSON_API_POST" && typeof candidate.path === "string";
}
