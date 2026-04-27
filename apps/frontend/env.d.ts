/// <reference types="vite/client" />

interface SonarRuntimeConfig {
  backendAddress?: string
  authToken?: string
}

interface Window {
  __SONAR_CONFIG__?: SonarRuntimeConfig
}
