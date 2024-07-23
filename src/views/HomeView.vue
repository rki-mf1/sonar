<template>
  <div class="input">
    <div class="input-left">
      <Button type="button" icon="pi pi-filter" label="&nbsp;Set Filters" severity="warning" raised
        :style="{ border: isFiltersSet ? '4px solid #cf3004' : '' }" @click="displayDialogFilter = true" />
      <Dialog v-model:visible="displayDialogFilter" modal header="Set Filters">
        <div style="display: flex; gap: 10px;">
          <div>
            <FilterGroup style="width: fit-content; margin: auto" :filterGroup="filterGroup"
              :propertyOptions="propertyOptions" :repliconAccessionOptions="repliconAccessionOptions"
              :lineageOptions="lineageOptions"
              :symbolOptions="symbolOptions" :operators="Object.values(DjangoFilterType)"
              :propertyValueOptions="propertyValueOptions"
              v-on:update-property-value-options="updatePropertyValueOptions" />
          </div>

        </div>
        <div style="display: flex; justify-content: end; gap: 10px;">
          <Button type="button" style="margin-top: 10px;" label="OK"
            @click="displayDialogFilter = false; updateSamples()"></Button>
        </div>
      </Dialog>
    </div>

    <div class="input-right">
      <Statistics :filteredCount="filteredCount"></Statistics>
    </div>
  </div>

  <div class="output_box">
    <div class="output">
      <div style="height: 100%; overflow: auto;">
        <Dialog v-model:visible="loading" modal :closable="false" header="Loading..." :style="{ width: '10vw' }">
          <ProgressSpinner size="small" v-if="loading" style="color: whitesmoke" />
        </Dialog>

        <Dialog v-model:visible="displayDialogRow" modal dismissableMask :style="{ width: '60vw' }">
          <template #header>
            <div style="display: flex; align-items: center;">
              <strong>Sample Details</strong>
              <router-link v-slot="{ href, navigate }" :to="`sample/${selectedRow.name}`" custom>
                <a :href="href" target="_blank" @click="navigate" style="margin-left: 8px;">
                  <i class="pi pi-external-link"></i>
                </a>
              </router-link>
            </div>
          </template>
          <SampleDetails :selectedRow="selectedRow" :allColumns="allColumns"></SampleDetails>
        </Dialog>

        <Dialog v-model:visible="displayDialogExport" header="Export Settings" modal dismissableMask
          :style="{ width: '25vw' }">

          <div>
            <RadioButton v-model="exportFormat" inputId="exportFormat1" value="csv" />
            <label for="exportFormat1" class="ml-2"> CSV (.csv)</label>
            <br><br>
            <RadioButton v-model="exportFormat" inputId="exportFormat2" value="xlsx" />
            <label for="exportFormat2" class="ml-2"> Excel (.xlsx)</label>
            <br><br>
          </div>

          <span><strong>Note: </strong>There is an export limit of maximum XXX samples!</span>

          <div style="display: flex; justify-content: end; gap: 10px; margin-top: 10px;">
            <Button icon="pi pi-external-link" label="&nbsp;Export" raised @click="exportFile(exportFormat)" />
          </div>
        </Dialog>

        <DataTable :value="samples" ref="dt" style="max-width: 90vw;" size="small" dataKey="name" stripedRows scrollable
          scrollHeight="flex" sortable @sort="sortingChanged($event)" v-model:selection="selectedRow"
          selectionMode="single" @rowSelect="onRowSelect" @rowUnselect="onRowUnselect">
          <template #empty> No Results </template>
          <template #header>
            <div style="display: flex; justify-content: space-between;">
              <div>
                <Button icon="pi pi-external-link" label="&nbsp;Export" raised @click="displayDialogExport = true" />
              </div>
              <div style="display: flex; justify-content: flex-end;">
                <MultiSelect v-model="selectedColumns" display="chip" :options="allColumns" filter
                  placeholder="Select Columns" class="w-full md:w-20rem" @update:modelValue="columnSelection">
                  <template #value>
                    <div style="margin-top: 5px; margin-left: 5px;">{{ selectedColumns.length }} columns selected
                    </div>
                  </template>
                </MultiSelect>
              </div>
            </div>
          </template>
          <Column field="name" sortable>
            <template #header>
              <span v-tooltip="metaDataCoverage('name')">ID</span>
            </template>
            <template #body="slotProps">
              <div
                style="height: 1.5em; width:9rem; text-overflow: ellipsis; overflow: hidden; white-space: nowrap; direction:rtl;"
                :title="slotProps.data.name">
                {{ slotProps.data.name }}
              </div>
            </template>
          </Column>
          <Column v-for="column in selectedColumns" :sortable="!notSortable.includes(column)" :field="column">
            <template #header>
              <span v-tooltip="metaDataCoverage(column)">{{ column }}</span>
            </template>
            <template #body="slotProps">
              <div v-if="column === 'genomic_profiles'">
                <div style="height: 1.5em; width:15rem; overflow-x: auto; white-space: nowrap;">
                  <GenomicProfileLabel v-for="(variant, index) in Object.keys(slotProps.data.genomic_profiles)"
                    :variantString="variant" :annotations="slotProps.data.genomic_profiles[variant]"
                    :isLast="index === Object.keys(slotProps.data.genomic_profiles).length - 1" />
                </div>
              </div>
              <div v-else-if="column === 'proteomic_profiles'">
                <div style="height: 1.5em; width:15rem; overflow-x: auto; white-space: nowrap;">
                  <GenomicProfileLabel v-for="(variant, index) in slotProps.data.proteomic_profiles"
                    :variantString="variant"
                    :isLast="index === Object.keys(slotProps.data.proteomic_profiles).length - 1" />
                </div>
              </div>
              <span v-else>
                {{ findProperty(slotProps.data.properties, column) }}
              </span>
            </template>
          </Column>
          <template #footer>
            <div style="display: flex; justify-content: space-between;">
              Total: {{ filteredCount }} Samples
            </div>
            <Paginator :totalRecords="filteredCount" v-model:rows="perPage"
              :rowsPerPageOptions="[10, 25, 50, 100, 1000, 10000, 100000]" v-model:first="firstRow"
              @update:rows="updateSamples()" />
          </template>
        </DataTable>
      </div>
      <div style="height: 100%; width: 30%; display: flex; justify-content: center;">
        <Chart type="bar" :data="chartData()" :options="chartOptions()" style="width: 80%;" />
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
  type FilterGroupRoot,
  type Property
} from '@/util/types'

export default {
  name: 'HomeView',
  data() {
    return {
      displayDialogFilter: false,
      selectedRow: null,
      displayDialogRow: false,
      displayDialogExport: false,
      exportFormat: 'csv',
      samples: [],
      filteredStatistics: {},
      filteredCount: 0,
      perPage: 10,
      firstRow: 0,
      page: 1,
      pages: 1,
      loading: false,
      isFiltersSet: false,
      ordering: '-collection_date',
      notSortable: ["genomic_profiles", "proteomic_profiles"],
      propertyOptions: [],
      repliconAccessionOptions: [],
      lineageOptions: [],
      allColumns: [],
      selectedColumns: ['sequencing_reason', 'collection_date', 'lineage', 'lab', 'zip_code', 'genomic_profiles'],
      propertyValueOptions: {} as {
        [key: string]: {
          options: string[];
          loading: boolean;
        };
      },
      symbolOptions: [],
      filterGroup: {
        filterGroups: [],
        filters: { propertyFilters: [], profileFilters: [], repliconFilters: [], lineageFilters: [] }
      } as FilterGroup,
      DjangoFilterType,
    };
  },
  methods: {
    async updateSamples() {
      this.loading = true;
      const params = {
        limit: this.perPage,
        offset: this.firstRow,
        ordering: this.ordering
      }
      this.samples = (await API.getInstance().getSampleGenomes(this.filters, params)).results;
      this.filteredStatistics = await API.getInstance().getFilteredStatistics(this.filters);
      this.filteredCount = this.filteredStatistics["filtered_total_count"];
      this.isFiltersSet = this.filters['filters']['andFilter'].length + this.filters['filters']['orFilter'].length > 0;
      this.loading = false;
    },
    columnSelection(value) {
      this.selectedColumns = value.filter(v => this.allColumns.includes(v));
    },
    onRowSelect(event) {
      this.selectedRow = event.data;
      this.displayDialogRow = true;
    },
    onRowUnselect(event) {
      this.selectedRow = null;
      this.displayDialogRow = false;
    },
    sortingChanged(sortBy) {
      if (sortBy.sortOrder > 0) {
        this.ordering = sortBy.sortField;
      } else {
        this.ordering = `-${sortBy.sortField}`;
      }
      this.updateSamples();
    },
    exportFile(type: string) {
      this.displayDialogExport = false;
      this.loading = true;
      API.getInstance().getSampleGenomesExport(this.filters, this.selectedColumns, type == "xlsx");
      this.loading = false;
    },
    metaDataCoverage(column: string) {
      if (this.filteredCount != 0 && this.filteredStatistics["meta_data_coverage"] != undefined) {
        const coverage = (this.filteredStatistics["meta_data_coverage"][column] / this.filteredCount * 100).toFixed(0);
        return 'Coverage: ' + coverage.toString() + ' %';
      } else {
        return '';
      }
    },
    chartData() {
      const samples_per_week = this.filteredStatistics["samples_per_week"];
      const labels: string[] = [];
      const data: number[] = [];

      if (samples_per_week != undefined) {
        Object.keys(samples_per_week).forEach(key => {
          labels.push(key);
          data.push(samples_per_week[key]);
        });
      }
      return {
        labels: labels,
        datasets: [
          {
            label: 'Samples',
            data: data,
            backgroundColor: 'rgba(249, 115, 22, 0.2)',
            borderColor: 'rgb(249, 115, 22)',
            borderWidth: 1
          }
        ]
      }
    },
    chartOptions() {
      const documentStyle = getComputedStyle(document.documentElement);
      const textColor = documentStyle.getPropertyValue('--text-color');
      const textColorSecondary = documentStyle.getPropertyValue('--text-color-secondary');
      const surfaceBorder = documentStyle.getPropertyValue('--surface-border');
      return {
        plugins: {
          legend: {
            display: false
          },
        },
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            ticks: {
              color: textColorSecondary
            },
            grid: {
              color: surfaceBorder
            }
          },
          y: {
            beginAtZero: true,
            ticks: {
              color: textColorSecondary
            },
            grid: {
              color: surfaceBorder
            }
          }
        }
      };
    },
    async updatePropertyOptions() {
      const res = await API.getInstance().getSampleGenomePropertyOptions();
      this.propertyOptions = res.property_names;
      this.allColumns = res.property_names.concat(['genomic_profiles', 'proteomic_profiles']).sort();
    },
    async updateRepliconAccessionOptions() {
      const res = await API.getInstance().getRepliconAccessionOptions();
      this.repliconAccessionOptions = res.accessions;
    },
    async updateLineageOptions() {
      const res = await API.getInstance().getLineageOptions();
      this.lineageOptions = res.lineages;
    },
    async updateSymbolOptions() {
      const res = await API.getInstance().getGeneSymbolOptions();
      this.symbolOptions = res.gene_symbols;
    },
    parseDateToDateRangeFilter(data) {
      data[0] = new Date(Date.parse(data[0].toString()));
      if (data[1]) {
        data[1] = new Date(Date.parse(data[1].toString()));
        const formatted = `${data[0].toISOString().split('T')[0]},${data[1].toISOString().split('T')[0]}`
        return formatted;
      } else {
        return `${data[0].toISOString().split('T')[0]},${new Date(
          Date.parse(data[0]) + 1000 * 60 * 60 * 24
        ).toISOString().split('T')[0]}`;
      }
    },
    getFilterGroupFilters(filterGroup: FilterGroup): FilterGroupFilters {
      const summary = {
        andFilter: [] as GenomeFilter[],
        orFilter: [] as FilterGroupFilters[]
      } as FilterGroupFilters;
      for (const filter of filterGroup.filters.propertyFilters) {
        if (filter.propertyName && filter.filterType && filter.value) {
          var value = filter.value;
          if (filter.propertyName.includes('date')) {
            if (value[1]) {
              filter.filterType = DjangoFilterType.RANGE;
              value = this.parseDateToDateRangeFilter(value);
            } else {
              value = new Date(value[0]).toISOString().split('T')[0];
            }
          }
          summary.andFilter.push({
            label: filter.label,
            property_name: filter.propertyName,
            filter_type: filter.filterType,
            value: value.toString()
          });
        }
      }
      for (const filter of filterGroup.filters.profileFilters) {
        var valid = true;
        const translatedFilter = {} as Record<string, string | number | boolean>;
        for (const key of Object.keys(filter) as (keyof ProfileFilter)[]) {
          //snake_case conversion
          var translatedKey = key.replace('AA', '_aa');
          translatedKey = translatedKey.replace(/([A-Z])/g, '_$1').toLowerCase();
          translatedFilter[translatedKey] = filter[key];
          if (!filter[key] && key != 'exclude') {
            valid = false;
            break;
          }
        }
        if (valid) {
          summary.andFilter.push(translatedFilter);
        }
      }
      for (const filter of filterGroup.filters.repliconFilters) {
        if (filter.accession) {
          summary.andFilter.push({
            label: filter.label,
            accession: filter.accession,
            exclude: filter.exclude
          });
        }
      }
      for (const filter of filterGroup.filters.lineageFilters) {
        if (filter.lineage) {
          summary.andFilter.push({
            label: filter.label,
            lineage: filter.lineage,
            exclude: filter.exclude
          });
        }
      }
      for (const subFilterGroup of filterGroup.filterGroups) {
        summary.orFilter.push(this.getFilterGroupFilters(subFilterGroup));
      }
      return summary;
    },
    updatePropertyValueOptions(propertyName: string) {
      if (this.propertyValueOptions[propertyName])
        return;
      this.propertyValueOptions[propertyName] = { loading: true, options: [] };
      API.getInstance()
        .getSampleGenomePropertyValueOptions(propertyName)
        .then((res) => {
          this.propertyValueOptions[propertyName].options = res.values;
          this.propertyValueOptions[propertyName].loading = false;
        });
    },
    findProperty(properties: Array<Property>, propertyName: string) {
      const property = properties.find(property => property.name === propertyName);
      return property ? property.value : undefined;
    }
  },
  computed: {
    filters(): FilterGroupRoot {

      const filters = {
        filters: this.getFilterGroupFilters(this.filterGroup),
      };
      return filters as FilterGroupRoot;
    }
  },
  mounted() {
    this.updateSamples();
    this.updatePropertyOptions();
    this.updateSymbolOptions();
    this.updateRepliconAccessionOptions();
    this.updateLineageOptions();
  }
}

</script>

<style scoped>
.input {
  height: 15%;
  width: 98%;
  display: flex;
  flex-direction: row;
  justify-content: space-evenly;
  align-items: center;
  background-color: var(--text-color);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: var(--shadow);
}

.input-left {
  height: 100%;
  width: 30%;
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  margin-left: 20px;
  align-items: center;
}

.input-right {
  height: 100%;
  width: 90%;
  display: flex;
  flex-direction: row;
  justify-content: flex-end;
  align-items: center;
}

.output_box {
  height: 80%;
  width: 98%;
  margin: 0 auto;
  display: flex;
  flex-direction: row;
  justify-content: center;
  align-items: center;
  background-color: white;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: var(--shadow);
}

.output {
  height: 95%;
  width: 98%;
  margin: 0 auto;
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
}

:deep(.p-button) {
  background: var(--primary-color);
  border: 1px solid var(--primary-color-darker);
}

:deep(.p-button):hover {
  background: var(--primary-color-lighter)
}

:deep(.p-button.p-button-outlined) {
  background: transparent;
  color: var(--primary-color);
}

:deep(.p-button.p-button-outlined):hover {
  background: rgb(248, 247, 247);
}

:deep(.p-button.p-button-warning) {
  background: var(--secondary-color);
  border: 1px solid var(--secondary-color-darker);
}

:deep(.p-button.p-button-warning):hover {
  background: var(--secondary-color-lighter);
}

:deep(.p-inputswitch.p-component.p-highlight .p-inputswitch-slider) {
  background: var(--primary-color);
}

:deep(.p-radiobutton .p-radiobutton-box .p-radiobutton-icon) {
  background: var(--primary-color);
}
</style>
