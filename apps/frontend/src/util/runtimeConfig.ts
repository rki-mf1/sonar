const normalizeBackendAddress = (value?: string) => {
  if (!value) {
    return value
  }

  return value.endsWith('/') ? value : `${value}/`
}

export const runtimeConfig = {
  backendAddress: normalizeBackendAddress(
    window.__SONAR_CONFIG__?.backendAddress ?? import.meta.env.VITE_SONAR_BACKEND_ADDRESS,
  ),
  authToken: window.__SONAR_CONFIG__?.authToken ?? import.meta.env.VITE_SONAR_AUTH_TOKEN,
}
