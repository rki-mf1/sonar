export enum DjangoFilterType {
  EXACT = 'exact',
  IEXACT = 'iexact',
  CONTAINS = 'contains',
  ICONTAINS = 'icontains',
  IN = 'in',
  GT = 'gt',
  GTE = 'gte',
  LT = 'lt',
  LTE = 'lte',
  STARTSWITH = 'startswith',
  ISTARTSWITH = 'istartswith',
  ENDSWITH = 'endswith',
  IENDSWITH = 'iendswith',
  RANGE = 'range',
  ISNULL = 'isnull',
  REGEX = 'regex',
  IREGEX = 'iregex',
}

export enum StringDjangoFilterType {
  EXACT = 'exact',
  CONTAINS = 'contains',
  REGEX = 'regex',
}

export enum DateDjangoFilterType {
  RANGE = 'range',
}

export enum IntegerDjangoFilterType {
  EXACT = 'exact',
  GT = 'gt',
  GTE = 'gte',
  LT = 'lt',
  LTE = 'lte',
  RANGE = 'range',
  IN = 'in',
}
export type PropertyFilter = {
  fetchOptions: boolean
  label: string
  value: string | number | string[] | Date[] | null
  propertyName: string
  filterType:
    | DateDjangoFilterType
    | IntegerDjangoFilterType
    | StringDjangoFilterType
    | DjangoFilterType
    | null
}

export type ProfileFilter = {
  label: string
  value: string
  exclude: boolean
}

export type RepliconFilter = {
  label: string
  accession: string
  exclude: boolean
}

export type LineageFilter = {
  label: string
  lineageList: string[]
  exclude: boolean
  includeSublineages: boolean
  isVisible: boolean
}

export type GenomeFilter = PropertyFilter | ProfileFilter

export type FilterGroupFilters = {
  andFilter: Record<string, string | number | boolean | string[]>[]
  orFilter: FilterGroupFilters[]
}

export type FilterGroupRoot = {
  limit?: number
  offset?: number
  filters: FilterGroupFilters
}

export type AndFilters = {
  propertyFilters: PropertyFilter[]
  profileFilters: ProfileFilter[]
  repliconFilters: RepliconFilter[]
  lineageFilter: LineageFilter // no AND filter possible for lineage, one sample has only one lineage
}

export type FilterGroup = {
  marked?: boolean
  filterGroups: FilterGroup[]
  filters: AndFilters
}

export type Property = {
  name: string
  value: string
}

export type GenomicProfile = {
  [key: string]: string[]
}

export type SampleDetails = {
  name: string
  properties: Property[]
  genomic_profiles: GenomicProfile
  proteomic_profiles: string[]
}

export type LineageBarChartData = {
  lineage: string
  week: string
  percentage: number
}

export type FilteredStatistics = {
  filtered_total_count: number
  meta_data_coverage: { [key: string]: number }
}

// TODO: too unflexibel, change to more flexible structure allowing different properties
export type FilteredStatisticsPlots = {
  samples_per_week: { [key: string]: number }
  genomecomplete_chart: { [key: string]: number }
  lineage_area_chart: Array<{ date: string; lineage: string; percentage: number }>
  lineage_bar_chart: LineageBarChartData[]
  lineage_grouped_bar_chart: Array<{ week: string; lineage_group: string; percentage: number }>
  sequencing_tech: { [key: string]: number }
  sequencing_reason: { [key: string]: number }
  sample_type: { [key: string]: number }
  length: { [key: string]: number }
  lab: { [key: string]: number }
  zip_code: { [key: string]: number }
  host: { [key: string]: number }
}

export type CustomPercentageLabelsOptions = {
  enabled: boolean
  threshold: number
}

export type RowSelectEvent<T = unknown> = {
  data: T
  index: number
  originalEvent: Event
  type: string
}

export type SelectedRowData = {
  name: string
  properties: never[]
  genomic_profiles: { [variant: string]: string[] }
  proteomic_profiles: string[]
}
