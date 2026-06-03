/// <reference types="vite/client" />

declare const __SONAR_VERSION__: string

interface SonarRuntimeConfig {
  backendAddress?: string
  authToken?: string
}

interface Window {
  __SONAR_CONFIG__?: SonarRuntimeConfig
}
