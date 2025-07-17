import { defineStore } from 'pinia'
import API from '@/api/API'
import {
  type FilterGroup,
  type FilterGroupRoot,
  type FilterGroupFilters,
  type GenomeFilter,
  type ProfileFilter,
  type Statistics,
  type FilteredStatistics,
  type FilteredStatisticsPlots,
  DjangoFilterType,
  StringDjangoFilterType,
  DateDjangoFilterType,
  type PropertyFilter,
} from '@/util/types'
import { reactive } from 'vue'
import { watch } from 'vue'

// called in getters, not allowed in actions
function getFilterGroupFilters(filterGroup: FilterGroup): FilterGroupFilters {
  const summary = {
    andFilter: [] as GenomeFilter[],
    orFilter: [] as FilterGroupFilters[],
  } as FilterGroupFilters
  for (const filter of filterGroup.filters.propertyFilters) {
    if (filter.propertyName && filter.filterType && filter.value) {
      let value = filter.value
      if (Array.isArray(filter.value) && filter.value.every((item) => item instanceof Date)) {
        const date_array = filter.value as Date[]
        if (date_array[1]) {
          filter.filterType = DjangoFilterType.RANGE
          value = parseDateToDateRangeFilter(date_array)
        } else {
          value = []
          //value = new Date(date_array[0]).toISOString().split('T')[0]
        }
      }
      summary.andFilter.push({
        label: filter.label,
        property_name: filter.propertyName,
        filter_type: filter.filterType,
        value: value.toString(),
      })
    }
  }
  for (const filter of filterGroup.filters.profileFilters) {
    let valid = true
    const translatedFilter = {} as Record<string, string | number | boolean>
    for (const key of Object.keys(filter) as (keyof ProfileFilter)[]) {
      //snake_case conversion
      let translatedKey = key.replace('AA', '_aa')
      translatedKey = translatedKey.replace(/([A-Z])/g, '_$1').toLowerCase()
      translatedFilter[translatedKey] = filter[key]
      if (!filter[key] && key != 'exclude') {
        valid = false
        break
      }
    }
    if (valid) {
      summary.andFilter.push(translatedFilter)
    }
  }
  for (const filter of filterGroup.filters.repliconFilters) {
    if (filter.accession) {
      summary.andFilter.push({
        label: filter.label,
        accession: filter.accession,
        exclude: filter.exclude,
      })
    }
  }
  if (
    filterGroup.filters.lineageFilter.lineageList &&
    filterGroup.filters.lineageFilter.lineageList.length > 0
  ) {
    summary.andFilter.push(filterGroup.filters.lineageFilter)
  }
  for (const subFilterGroup of filterGroup.filterGroups) {
    summary.orFilter.push(getFilterGroupFilters(subFilterGroup))
  }
  return summary
}

function parseDateToDateRangeFilter(data: Date[]) {
  // Parse the first date
  data[0] = new Date(Date.parse(data[0].toString()))
  //  format the date according to your local timezone instead of UTC.
  const formatDateToLocal = (date: Date) => {
    return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().split('T')[0]
  }

  // Check if there's a second date
  if (data[1]) {
    data[1] = new Date(Date.parse(data[1].toString()))
    const formatted = [formatDateToLocal(data[0]), formatDateToLocal(data[1])]
    return formatted
  } else {
    // If there's no second date, assume a range of one day?
    const nextDay = new Date(Date.parse(data[0].toString()) + 1000 * 60 * 60 * 24)
    return [formatDateToLocal(data[0]), formatDateToLocal(nextDay)]
  }
}

export const useSamplesStore = defineStore('samples', {
  state: () => ({
    organism: null as string | null,
    accession: null as string | null,
    data_sets: [] as string[],
    samples: [],
    statistics: {} as Statistics,
    filteredStatistics: {} as FilteredStatistics,
    filteredStatisticsPlots: {} as FilteredStatisticsPlots,
    filteredCount: 0,
    loading: false,
    perPage: 10,
    firstRow: 0,
    filtersChanged: false,
    ordering: '-collection_date' as string,
    timeRange: [] as (Date | null)[],
    propertiesDict: {} as { [key: string]: string[] },
    propertyTableOptions: [] as string[],
    propertyMenuOptions: [] as string[],
    metaCoverageOptions: [] as string[],
    selectedColumns: ['genomic_profiles', 'proteomic_profiles'],
    propertyValueOptions: {} as {
      [key: string]: {
        options: string[]
        loading: boolean
      }
    },
    repliconAccessionOptions: [] as string[],
    lineageOptions: [] as string[],
    symbolOptions: [] as string[],
    filterGroup: reactive({
      filterGroups: [],
      filters: {
        propertyFilters: [
          {
            fetchOptions: false,
            label: 'Property',
            propertyName: 'collection_date',
            filterType: DateDjangoFilterType.RANGE,
            value: [] as (Date | null)[],
          },
        ],
        profileFilters: [{ label: 'DNA/AA Profile', value: '', exclude: false }],
        repliconFilters: [],
        lineageFilter: {
          label: 'Lineages',
          lineageList: [],
          exclude: false,
          includeSublineages: true,
          isVisible: true,
        }, // first lineage filter always shown
      },
    }) as FilterGroup,
    DjangoFilterType,
    errorMessage: '',
    lastSentFilterGroup: JSON.stringify({
      filterGroups: [],
      filters: {
        propertyFilters: [],
        profileFilters: [],
        repliconFilters: [],
        lineageFilter: {
          label: 'Lineages',
          lineageList: [],
          exclude: false,
          includeSublineages: true,
          isVisible: true,
        },
      },
    }),
  }),
  actions: {
    setDataset(organism: string | null, accession: string | null, data_sets: string[]) {
      this.organism = organism
      this.accession = accession
      this.data_sets = data_sets
    },
    async updateStatistics() {
      const emptyStatistics = {
        samples_total: 0,
        first_sample_date: '',
        latest_sample_date: '',
        populated_metadata_fields: [],
      }
      try {
        const statistics = await API.getInstance().getSampleStatistics(this.accession)
        if (!statistics) {
          this.statistics = emptyStatistics
        } else {
          this.statistics = statistics
        }
      } catch (error) {
        // TODO how to handle request failure
        console.error('Error fetching statistics:', error)
        this.statistics = emptyStatistics
      }
    },
    async updateSamples() {
      this.errorMessage = ''
      this.loading = true
      const params = {
        limit: this.perPage,
        offset: this.firstRow,
        ordering: this.ordering,
      }
      this.lastSentFilterGroup = JSON.stringify(this.filterGroup)
      const response = await API.getInstance().getSampleGenomes(this.filters, params)
      // Handle errors
      if (response.response && response.response.status) {
        const status = response.response.status
        if (status >= 400 && status < 500) {
          this.errorMessage = 'Client error:\n' + response.response.data.detail
        } else if (status >= 500) {
          this.errorMessage = 'Server error occurred. Please try again later.'
        } else {
          this.errorMessage = 'An unknown error occurred.'
        }
      } else {
        this.samples = response.results
      }
      this.loading = false
      this.filtersChanged = false
    },
    async updateFilteredStatistics() {
      const emptyStatistics = {
        filtered_total_count: 0,
      }
      try {
        const filteredStatistics = await API.getInstance().getFilteredStatistics(this.filters)
        if (!filteredStatistics) {
          this.filteredStatistics = emptyStatistics
        } else {
          this.filteredStatistics = filteredStatistics
        }
        this.filteredCount = this.filteredStatistics.filtered_total_count
      } catch (error) {
        // TODO how to handle request failure
        console.error('Error fetching filtered statistics:', error)
        this.filteredStatistics = emptyStatistics
        this.filteredCount = 0
      }
    },
    async updateFilteredStatisticsPlots() {
      const emptyStatistics = {
        samples_per_week: {},
        meta_data_coverage: {},
        genomecomplete_chart: {},
        lineage_area_chart: [],
        lineage_bar_chart: [],
        lineage_grouped_bar_chart: [],
        sequencing_tech: {},
        sequencing_reason: {},
        sample_type: {},
        length: {},
        lab: {},
        zip_code: {},
        host: {},
      }
      try {
        const filteredStatisticsPlots = await API.getInstance().getFilteredStatisticsPlots(
          this.filters,
        )
        if (!filteredStatisticsPlots) {
          this.filteredStatisticsPlots = emptyStatistics
        } else {
          this.filteredStatisticsPlots = filteredStatisticsPlots
        }
      } catch (error) {
        // TODO how to handle request failure
        console.error('Error fetching filtered statistics plots:', error)
        this.filteredStatisticsPlots = emptyStatistics
      }
    },
    async setDefaultTimeRange() {
      this.timeRange = [
        new Date(this.statistics.first_sample_date),
        new Date(this.statistics.latest_sample_date ?? Date.now()),
      ]
      return this.timeRange
    },
    updatePropertyValueOptions(filter: PropertyFilter) {
      const propertyName = filter.propertyName
      if (this.propertyValueOptions[propertyName]) return
      this.propertyValueOptions[propertyName] = { loading: true, options: [] }
      API.getInstance()
        .getSampleGenomePropertyValueOptions(propertyName, this.accession)
        .then((res) => {
          this.propertyValueOptions[propertyName].options = res.values
          this.propertyValueOptions[propertyName].loading = false
        })
    },

    async updateSelectedColumns() {
      const properties = [
        'lineage',
        'collection_date',
        'zip_code',
        'lab',
        'sequencing_tech',
        'sequencing_reason',
        'isolation_source',
        'init_upload_date',
        'last_update_date',
      ]
      let columns = [
        ...this.selectedColumns,
        ...properties.filter((prop) => this.propertyTableOptions.includes(prop)),
      ]
      columns = [...columns, ...this.propertyTableOptions.filter((prop) => !columns.includes(prop))]
      this.selectedColumns = columns.slice(0, 6)
    },

    async updatePropertyOptions() {
      try {
        const res = await API.getInstance().getSampleGenomePropertyOptionsAndTypes()
        if (!res) {
          console.error('API request failed')
          return
        }
        const metaData = this.statistics?.populated_metadata_fields ?? []
        this.propertiesDict = {}
        res.values.forEach(
          (property: { name: string; query_type: string; description: string }) => {
            if (property.query_type === 'value_varchar') {
              this.propertiesDict[property.name] = Object.values(StringDjangoFilterType)
            } else if (property.query_type === 'value_date') {
              this.propertiesDict[property.name] = Object.values(DateDjangoFilterType)
            } else {
              this.propertiesDict[property.name] = Object.values(DjangoFilterType)
            }
          },
        )
        // keep only those properties that have a coverage, i.e. that are not entirly empty
        // & drop the 'name' column because the ID column is fixed
        this.propertyTableOptions = Object.keys(this.propertiesDict).filter(
          (key) => key !== 'name' && metaData.includes(key),
        )
        this.propertyMenuOptions = [
          'name',
          ...this.propertyTableOptions.filter(
            (prop) => !['genomic_profiles', 'proteomic_profiles', 'lineage'].includes(prop),
          ),
        ]
        this.metaCoverageOptions = [
          ...this.propertyMenuOptions.filter(
            (prop) => !['name', 'init_upload_date', 'last_update_date'].includes(prop),
          ),
        ]
      } catch (error) {
        console.error('Failed to update property options:', error)
      }
    },
    async updateRepliconAccessionOptions() {
      const res = await API.getInstance().getRepliconAccessionOptions(this.accession)
      this.repliconAccessionOptions = res.accessions
    },
    async updateLineageOptions() {
      const res = await API.getInstance().getLineageOptions(this.accession)
      this.lineageOptions = res.lineages
    },
    async updateSymbolOptions() {
      const res = await API.getInstance().getGeneSymbolOptions(this.accession)
      this.symbolOptions = res.gene_symbols
    },
    isDateArray(value: unknown): value is Date[] {
      return Array.isArray(value) && value.every((item) => item instanceof Date)
    },

    initializeWatchers() {
      watch(
        () => this.filterGroup,
        (newFilters) => {
          if (JSON.stringify(newFilters) !== this.lastSentFilterGroup) {
            this.filtersChanged = true
          } else {
            this.filtersChanged = false
          }
        },
        { deep: true },
      )
    },
  },
  getters: {
    filterGroupsFilters(): FilterGroupRoot {
      return { filters: getFilterGroupFilters(this.filterGroup) }
    },
    filters(): FilterGroupRoot {
      const filters = JSON.parse(JSON.stringify(this.filterGroupsFilters)) as FilterGroupRoot

      if (!filters.filters?.andFilter) {
        filters.filters.andFilter = []
      }

      // insert dataset selection as a fixed filter at the beginning
      if (this.data_sets?.length > 0) {
        this.data_sets = this.data_sets.map((value) => (value === '-Empty-' ? '' : value))
        filters.filters.andFilter.unshift({
          label: 'Property',
          property_name: 'data_set',
          filter_type: 'in',
          value: this.data_sets,
        })
      }
      if (this.accession) {
        filters.filters.andFilter.unshift({
          label: 'Reference',
          exclude: false,
          accession: this.accession,
        })
      }

      return filters
    },
  },
})

let storeInitialized = false

export function initializeStore() {
  useSamplesStore()

  if (!storeInitialized) {
    storeInitialized = true
  }
}
