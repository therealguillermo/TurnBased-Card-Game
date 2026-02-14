/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_NAKAMA_URL: string
  readonly VITE_NAKAMA_SERVER_KEY: string
  readonly VITE_GENERATION_URL: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
