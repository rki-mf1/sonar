import type { ChartOptions } from 'chart.js'

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

export enum PlotType {
  bar = 'bar',
  histogram = 'histogram',
  scatter = 'scatter',
  doughnut = 'doughnut',
  line = 'line',
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

export type Statistics = {
  samples_total: number
  first_sample_date: string
  latest_sample_date: string
  populated_metadata_fields: string[]
}

export type FilteredStatistics = {
  filtered_total_count: number
}

export type SamplesPerWeek = [string, number]

export type LineagePerWeek = {
  week: string
  lineage_group: string
  count: number
  percentage: number
}
export type PlotMetadataCoverage = {
  metadata_coverage: { [key: string]: number }
}
export type PlotCustom = {
  custom_property: { [key: string]: number }
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

export type PlotDataSets =
  | {
      label: string
      data: number[]
      backgroundColor: string
      borderColor: string
      borderWidth: number
    }
  | {
      label: string
      data: never[]
    }
export type HistogramData = {
  labels: string[] // Array of strings representing bin ranges
  datasets: Array<PlotDataSets>
}

export type SimplePlotData = {
  labels: string[]
  datasets: PlotDataSets[]
}

export type ScatterPlotData = {
  labels: string[]
  datasets: {
    label: string
    data: {
      x: number | Date | string
      y: number | Date | string
    }[]
    backgroundColor: string
    borderColor: string
    borderWidth: number
  }[]
}

export type PlotData = {
  labels: string[]
  datasets: {
    label: string
    data: never[]
  }[]
}

export type PlotConfig = {
  type: PlotType | null
  propertyName: string | null
  plotTitle: string
  data: HistogramData | SimplePlotData | ScatterPlotData | undefined
  options: ChartOptions
}
