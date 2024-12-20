/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly BACKEND_PORT: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}