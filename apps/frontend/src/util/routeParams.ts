// helper functions for handling route parameters related to user's dataset selection in Home to ensure clean query strings

export function safeDecodeURIComponent(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch (error) {
    console.warn('Failed to decode route segment', value, error)
    return value
  }
}

export function decodeDatasetsParam(source: unknown): (string | null)[] {
  if (Array.isArray(source)) {
    return source.map(mapDatasetValue)
  }
  if (source !== undefined && source !== null) {
    return [mapDatasetValue(source)]
  }
  return []
}

export function buildSelectionQuery(accession: string | null, datasets: (string | null)[]) {
  const query: Record<string, string | string[]> = {}
  if (accession) {
    query.accession = accession
  }
  if (datasets?.length) {
    query.dataset = datasets.map((value) => value ?? '')
  }
  return query
}

function mapDatasetValue(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null
  }
  const stringValue = String(value)
  return stringValue.length === 0 ? '' : safeDecodeURIComponent(stringValue)
}
