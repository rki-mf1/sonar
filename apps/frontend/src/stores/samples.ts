import { defineStore } from 'pinia';
import API from '@/api/API';
import {
  type FilterGroup,
  type FilterGroupRoot,
  type FilterGroupFilters,
  type GenomeFilter,
  type ProfileFilter,
  type LineageFilter,
  type PropertyFilter,
  type Property,
  DjangoFilterType,
  StringDjangoFilterType,
  DateDjangoFilterType
} from '@/util/types'
import { reactive } from 'vue';
import { watch, ref } from 'vue';

export const useSamplesStore = defineStore('samples', {
  state: () => ({
    samples: [],
    filteredStatistics: {},
    filteredCount: 0,
    loading: false,
    perPage: 10,
    firstRow: 0,
    filtersChanged: false,
    ordering: '-collection_date',
    timeRange: [] as (Date | null)[],
    propertiesDict: {} as { [key: string]: string[] },
    propertyOptions: [] as string[],
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
        propertyFilters: [],
        profileFilters: [{"label":"Label","value":"","exclude":false}],
        repliconFilters: [],
        lineageFilter: {
          label: "Lineages",
          lineageList: [],
          exclude: false,
          includeSublineages: true,
          isVisible: true,} // first lineage filter always shown
      } 
  }) as FilterGroup,
  DjangoFilterType,
  errorMessage: '',
  
    DjangoFilterType,
    errorMessage: '',
    lastSentFilterGroup: JSON.stringify({
      filterGroups: [],
      filters: {
        propertyFilters: [],
        profileFilters: [],
        repliconFilters: [],
        lineageFilter: {
          label: "Lineages",
          lineageList: [],
          exclude: false,
          includeSublineages: true,
          isVisible: true
        }
      }
    })
  }),
  actions: {
    async updateSamples() {
      this.errorMessage = ''
      this.loading = true
      const params = {
        limit: this.perPage,
        offset: this.firstRow,
        ordering: this.ordering
      }
      this.lastSentFilterGroup = JSON.stringify(this.filterGroup);
      var response = (await API.getInstance().getSampleGenomes(this.filters, params))
      // Handle errors
      if (response.response && response.response.status) {
        const status = response.response.status;
        if (status >= 400 && status < 500) {
          this.errorMessage = 'Client error:\n'+ response.response.data.detail;
        } else if (status >= 500) {
          this.errorMessage = 'Server error occurred. Please try again later.';
        } else {
          this.errorMessage = 'An unknown error occurred.';
        }
      }else{
        this.samples = response.results;
        this.filteredStatistics = await API.getInstance().getFilteredStatistics(this.filters)
        this.filteredCount = this.filteredStatistics.filtered_total_count

      }
      this.loading = false
      this.filtersChanged = false
    },
    async setDefaultTimeRange() {
      const statistics = await API.getInstance().getSampleStatistics()
      this.timeRange = [
        new Date(statistics.first_sample_date),
        new Date(statistics.latest_sample_date ?? Date.now())
      ]
      this.updateSamples()
    },
    updatePropertyValueOptions(propertyName: string) {
      if (this.propertyValueOptions[propertyName]) return
      this.propertyValueOptions[propertyName] = { loading: true, options: [] }
      API.getInstance()
        .getSampleGenomePropertyValueOptions(propertyName)
        .then((res) => {
          this.propertyValueOptions[propertyName].options = res.values
          this.propertyValueOptions[propertyName].loading = false
        })
    },
    async updatePropertyOptions() {
      const res = await API.getInstance().getSampleGenomePropertyOptionsAndTypes()
      this.propertiesDict = {}
      res.values.forEach((property: { name: string, query_type: string, description: string }) => {
        if (property.query_type === 'value_varchar') {
          this.propertiesDict[property.name] = Object.values(StringDjangoFilterType);
        } else if (property.query_type === 'value_date') {
          this.propertiesDict[property.name] = Object.values(DateDjangoFilterType);
        } else {
          this.propertiesDict[property.name] = Object.values(DjangoFilterType);
        }
      });
      this.propertyOptions = Object.keys(this.propertiesDict)
    },
    async updateRepliconAccessionOptions() {
      const res = await API.getInstance().getRepliconAccessionOptions()
      this.repliconAccessionOptions = res.accessions
    },
    async updateLineageOptions() {
      const res = await API.getInstance().getLineageOptions()
      this.lineageOptions = res.lineages
    },
    async updateSymbolOptions() {
      const res = await API.getInstance().getGeneSymbolOptions()
      this.symbolOptions = res.gene_symbols
    },
    getFilterGroupFilters(filterGroup: FilterGroup): FilterGroupFilters {
      const summary = {
        andFilter: [] as GenomeFilter[],
        orFilter: [] as FilterGroupFilters[]
      } as FilterGroupFilters
      for (const filter of filterGroup.filters.propertyFilters) {
        if (filter.propertyName && filter.filterType && filter.value) {
          var value = filter.value
          if (filter.propertyName.includes('date')) {
            if (value[1]) {
              filter.filterType = DjangoFilterType.RANGE
              value = this.parseDateToDateRangeFilter(value)
            } else {
              value = new Date(value[0]).toISOString().split('T')[0]
            }
          }
          summary.andFilter.push({
            label: filter.label,
            property_name: filter.propertyName,
            filter_type: filter.filterType,
            value: value.toString()
          })
        }
      }
      for (const filter of filterGroup.filters.profileFilters) {
        var valid = true
        const translatedFilter = {} as Record<string, string | number | boolean>
        for (const key of Object.keys(filter) as (keyof ProfileFilter)[]) {
          //snake_case conversion
          var translatedKey = key.replace('AA', '_aa')
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
            exclude: filter.exclude
          })
        }
      }
      if (filterGroup.filters.lineageFilter.lineageList 
            && filterGroup.filters.lineageFilter.lineageList.length > 0) {
          summary.andFilter.push(filterGroup.filters.lineageFilter)
      }
      for (const subFilterGroup of filterGroup.filterGroups) {
        summary.orFilter.push(this.getFilterGroupFilters(subFilterGroup))
      }
      return summary
    },
    parseDateToDateRangeFilter(data) {
      // Parse the first date
      data[0] = new Date(Date.parse(data[0].toString()))
      //  format the date according to your local timezone instead of UTC.
      const formatDateToLocal = (date) => {
        return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
          .toISOString()
          .split('T')[0]
      }

      // Check if there's a second date
      if (data[1]) {
        data[1] = new Date(Date.parse(data[1].toString()))
        const formatted = [formatDateToLocal(data[0]), formatDateToLocal(data[1])]
        return formatted
      } else {
        // If there's no second date, assume a range of one day?
        const nextDay = new Date(Date.parse(data[0]) + 1000 * 60 * 60 * 24)
        return [formatDateToLocal(data[0]), formatDateToLocal(nextDay)]
      }
    },
    initializeWatchers() {
    watch(
      () => this.filterGroup,
      (newFilters, oldFilters) => {
        if (JSON.stringify(newFilters) !== this.lastSentFilterGroup) {
          this.filtersChanged = true;  
        } else {
          this.filtersChanged = false; 
        }
      },
      { deep: true }
    );
  },
},
  getters: {
    filterGroupsFilters(state): FilterGroupRoot {
      return { filters: this.getFilterGroupFilters(this.filterGroup) }
    },
    filterGroupFiltersHasDateFilter(state): boolean {
      return this.filterGroupsFilters.filters.andFilter.some(item => item.property_name === "collection_date") || this.filterGroupsFilters.filters.orFilter.some(item => item.property_name === "collection_date");
    },
    filters(state): FilterGroupRoot {
      const filters = JSON.parse(JSON.stringify(this.filterGroupsFilters));
      if (!filters.filters?.andFilter) {
        filters.filters.andFilter = []
      }

      if (this.timeRange[0] && this.timeRange[1] && !this.filterGroupFiltersHasDateFilter) {
        filters.filters.andFilter.push({
          label: 'Property',
          property_name: 'collection_date',
          filter_type: 'range',
          value: `${this.timeRange[0].toLocaleDateString('en-CA')},${this.timeRange[1].toLocaleDateString('en-CA')}` // formatted as "yyyy-mm-dd,yyyy-mm-dd"
        })
      }

      // if (this.filterGroupFiltersHasDateFilter) {
      //   this.timeRange = ''
      // }
      // else {
      //   this.setDefaultTimeRange()
      // }

      return filters as FilterGroupRoot
    }
  }
});

let storeInitialized = false;

export function initializeStore() {
  const store = useSamplesStore();

  if (!storeInitialized) {
    storeInitialized = true;


  }
}
