/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BACKEND_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}

declare const chrome: {
  runtime: {
    id?: string;
    getURL: (path: string) => string;
    sendMessage: (message: unknown) => Promise<unknown>;
    onMessage: {
      addListener: (
        callback: (
          message: unknown,
          sender: unknown,
          sendResponse: (response: unknown) => void
        ) => boolean | void
      ) => void;
    };
  };
};
