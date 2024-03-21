<template>
  <div style="height: 90vh; width: 90vw; display: flex; flex-direction: column">
    <div>
      <FilterGroup
        style="width: fit-content; margin: auto"
        :filterGroup="filterGroup"
        :propertyOptions="propertyOptions"
        :repliconAccessionOptions="repliconAccessionOptions"
        :symbolOptions="symbolOptions"
        :operators="Object.values(DjangoFilterType)"
        :propertyValueOptions="propertyValueOptions"
        v-on:update-property-value-options="updatePropertyValueOptions"
      />
    </div>
    <div style="flex-direction: column; display: flex">
      <div style="flex: auto; margin: auto">
        <Button size="small" @click="updateSamples()"
          ><i class="pi pi-list" /> &nbsp; Request Data</Button
        >
        <!-- <Button size="small" @click="requestExport()">
          <i class="pi pi-cloud-download" />Request export</Button
        > -->
      </div>
      <ProgressSpinner size="small" v-if="loading" style="color: whitesmoke" />
      <div v-if="samples" style="flex: auto">
        <h4>{{ sampleCount }} Results</h4>
        <Paginator
          :totalRecords="sampleCount"
          :rows="perPage"
          :rowsPerPageOptions="[10, 25, 50, 100, 1000, 10000, 100000]"
          v-model:first="firstRow"
          @update:first="updateSamples()"
        />
        <DataTable :value="samples" style="max-width: 90vw;">
          <Column field="name" header="Name"></Column>
          <Column field="properties" header="Properties">
            <template #body="slotProps">
              <table>
                <tr v-for="property in slotProps.data.properties" :key="property.name">
                  <td>{{ property.name }}</td>
                  <td>{{ property.value }}</td>
                </tr>
              </table>
            </template>
          </Column>
          <Column field="genomic_profiles" header="Genomic Profiles">
            <template #body="slotProps">
              {{ slotProps.data.genomic_profiles }}
            </template>
          </Column>
          <Column field="proteomic_profiles" header="Proteomic Profiles">
            <template #body="slotProps">
              {{ slotProps.data.proteomic_profiles }}
            </template></Column
          >
        </DataTable>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import API from '@/api/API'
import {
  type FilterGroup,
  DjangoFilterType,
  type GenomeFilter,
  type ProfileFilter,
  type FilterGroupFilters,
  type FilterGroupRoot
} from '@/util/types'
export default {
  name: 'GenomeFilterPage',
  data() {
    return {
      perPage: 10,
      firstRow: 0,
      page: 1,
      pages: 1,
      sampleCount: 0,
      samples: [],
      loading: false,
      propertyOptions: [],
      repliconAccessionOptions: [],
      propertyValueOptions: {} as { [key: string]: { options: string[]; loading: boolean } },
      symbolOptions: [],
      filterGroup: {
        filterGroups: [],
        filters: { propertyFilters: [], profileFilters: [], repliconFilters: []}
      } as FilterGroup,
      DjangoFilterType
    }
  },
  methods: {
    async updateSamples() {
      this.loading = true
      const res = await API.getInstance().getSampleGenomes(this.filters)
      this.samples = res.results
      this.sampleCount = res.count
      this.pages = res.count / this.perPage
      this.loading = false
    },
    async requestExport() {
      await API.getInstance().getSampleGenomesExport(this.filters)
    },
    async updatePropertyOptions() {
      const res = await API.getInstance().getSampleGenomePropertyOptions()
      this.propertyOptions = res.property_names
    },
    async updateRepliconAccessionOptions() {
      const res = await API.getInstance().getRepliconAccessionOptions()
      this.repliconAccessionOptions = res.accessions
    },
    async updateSymbolOptions() {
      const res = await API.getInstance().getGeneSymbolOptions()
      console.log(res)
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
            value = new Date(value).toISOString().split('T')[0]
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
      for (const subFilterGroup of filterGroup.filterGroups) {
        summary.orFilter.push(this.getFilterGroupFilters(subFilterGroup))
      }
      return summary
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
    }
  },
  computed: {
    filters(): FilterGroupRoot {
      const filters = {
        filters: this.getFilterGroupFilters(this.filterGroup),
        limit: this.perPage,
        offset: this.firstRow
      }
      return filters as FilterGroupRoot
    }
  },
  mounted() {
    this.updatePropertyOptions()
    this.updateSymbolOptions()
    this.updateRepliconAccessionOptions()
  }
}
</script>
