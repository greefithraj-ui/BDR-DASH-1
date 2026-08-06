/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_BIP_API_BASE_URL?: string;
  readonly VITE_BIP_API_PROXY_TARGET?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
