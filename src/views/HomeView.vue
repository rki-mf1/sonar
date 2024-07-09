
<template>
  <body>
    <main>
      <header>
        <i class="pi pi-spinner"
          style="font-size: 3rem; color: var(--text-color); margin-top: 10px; margin-bottom: 10px;"></i>
        <div style="font-size: 2rem; color: var(--text-color); margin-top: 10px;">ovSonar</div>
        <div class="menu">
          <Menubar :model="menu_items" />
        </div>

        <!-- <v-icon name="pr-spinner" scale="5" animation="float" style="color: white;"/> -->
        <!-- <div style="margin-bottom: 100px;"></div>
        <router-link to="/" class="nav-item">Home</router-link>
        <router-link to="/about" class="nav-item">About</router-link> -->
      </header>
      <div class="content">
        <div class="input">
          <div class="input-left">
            <Button type="button" icon="pi pi-filter" label="&nbsp;Set Filters" severity="warning" raised
              :style="{ border: isFiltersSet ? '4px solid #cf3004' : '' }" @click="displayDialogFilter = true" />
            <Dialog v-model:visible="displayDialogFilter" modal header="Set Filters">
              <div style="display: flex; gap: 10px;">
                <div>
                  <FilterGroup style="width: fit-content; margin: auto" :filterGroup="filterGroup"
                    :propertyOptions="propertyOptions" :repliconAccessionOptions="repliconAccessionOptions"
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
            <i class="pi pi-arrow-right" style="font-size: 1.5rem; color: var(--grayish);"></i>
            <Button type="button" icon="pi pi-list" label="&nbsp;Get Data" raised @click="updateSamples()" />
          </div>

          <div class="input-right">
            <Statistics></Statistics>
          </div>
        </div>

        <div class="output_box">
          <div class="output">
            <div style="height: 100%; overflow: auto;">
              <Dialog v-model:visible="loading" modal :closable="false" header="Loading..." :style="{ width: '10vw' }">
                <ProgressSpinner size="small" v-if="loading" style="color: whitesmoke" />
              </Dialog>
              <!-- Dialog for displaying row details -->
              <Dialog v-model:visible="displayDialogRow" modal dismissableMask header="Sequence Details" :style="{ width: '60vw' }">
                <div v-if="selectedRow">
                  <p v-for="(value, key) in selectedRow" :key="key">
                  <p v-if="allColumns.includes(key)">
                    <template v-if="key === 'genomic_profiles'">
                      <strong>{{ key }}: </strong>
                      <div style="white-space: normal; word-wrap: break-word;">
                        <GenomicProfileLabel v-for="(variant, index) in Object.keys(value)" :variantString="variant"
                          :annotations="value[variant]" :isLast="index === Object.keys(value).length - 1" />
                      </div>
                    </template>
                    <template v-else-if="key === 'proteomic_profiles'">
                      <strong>{{ key }}: </strong>
                      <div style="white-space: normal; word-wrap: break-word;">
                        <GenomicProfileLabel v-for="(variant, index) in value" :variantString="variant"
                          :isLast="index === Object.keys(value).length - 1" />
                      </div>
                    </template>
                    <template v-else-if="key === 'properties'">
                      <strong>{{ key }}:</strong>
                      <div v-for="item in value" :key="item.name">
                        <div v-if="item.name === 'lineage'">
                          <strong>&nbsp;&nbsp;&nbsp;{{ item.name }}:</strong> {{ item.value }} (<a
                            :href="'https://outbreak.info/situation-reports?pango=' + item.value" target="_blank">outbreak.info</a>)
                        </div>
                        <div v-else>
                          <strong>&nbsp;&nbsp;&nbsp;{{ item.name }}:</strong> {{ item.value }}
                        </div>
                      </div>
                    </template>
                    <template v-else>
                      <strong>{{ key }}:</strong> {{ value }}
                    </template>
                  </p>
                  </p>
                </div>
              </Dialog>
              <DataTable :value="samples" ref="dt" style="max-width: 90vw;" size="small" dataKey="name" stripedRows
                scrollable scrollHeight="flex"
                sortable removableSort @sort="sortingChanged($event)" 
                v-model:selection="selectedRow" selectionMode="single" @rowSelect="onRowSelect" @rowUnselect="onRowUnselect">
                <template #empty> No Results </template>
                <template #header>
                  <div style="display: flex; justify-content: space-between;">
                    <div>
                      <Button icon="pi pi-external-link" label="&nbsp;Export Data" raised @click="exportCSV($event)" />
                      <!-- <Button icon="pi pi-external-link" label="&nbsp;Export Data" raised @click="requestExport()" /> -->
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
                <Column v-for="column in selectedColumns" sortable :field="column">
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
                    Total: {{ filteredStatistics?.filtered_total_count ?? 0 }} Samples
                  </div>
                </template>
              </DataTable>
            </div>
            <div style="height: 100%; width: 30%; display: flex; justify-content: center;">
              <Chart type="bar" :data="chartData()" :options="chartOptions()" style="width: 80%;" />
            </div>
          </div>
        </div>
      </div>
    </main>
  </body>
</template>

<script lang="ts">

import API from '@/api/API'
import { useRouter } from 'vue-router';
import { FilterMatchMode } from 'primevue/api';
import GenomicProfileLabel from '@/components/GenomicProfileLabel.vue';
import {
  type FilterGroup,
  DjangoFilterType,
  type GenomeFilter,
  type ProfileFilter,
  type FilterGroupFilters,
  type FilterGroupRoot,
  type Property
} from '@/util/types'
import type GenomicProfileLabelVue from '@/components/GenomicProfileLabel.vue';

export default {
  name: 'HomeView',
  data() {
    return {
      router: useRouter(),
      menu_items: [
        {
          label: 'Home',
          icon: 'pi pi-home',
          route: '/'
        },
        {
          label: 'About',
          icon: 'pi pi-star',
          route: '/about'
        }
      ],
      // perPage: 10,
      // firstRow: 0,
      // page: 1,
      // pages: 1,
      displayDialogFilter: false,
      selectedRow: null,
      displayDialogRow: false,
      samples: [],
      filteredStatistics: {},
      loading: false,
      isFiltersSet: false,
      ordering: '-collection_date',
      propertyOptions: [],
      repliconAccessionOptions: [],
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
        filters: { propertyFilters: [], profileFilters: [], repliconFilters: [] }
      } as FilterGroup,
      DjangoFilterType,
    };
  },
  methods: {
    async updateSamples() {
      this.loading = true;
      const res = await API.getInstance().getSampleGenomes(this.filters, this.ordering);
      this.filteredStatistics = await API.getInstance().getFilteredStatistics(this.filters);
      this.samples = res.results;
      this.isFiltersSet = !(this.filters['filters']['andFilter'].length === 0 && this.filters['filters']['orFilter'].length === 0);
      // this.pages = res.count / this.perPage
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
    metaDataCoverage(column: string) {
      if (this.filteredStatistics["filtered_total_count"] != undefined) {
        const coverage = (this.filteredStatistics["meta_data_coverage"][column] / this.filteredStatistics["filtered_total_count"] * 100).toFixed(0);
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
    exportCSV() {
      this.$refs.dt.exportCSV();
    },
    // async requestExport() {
    //   await API.getInstance().getSampleGenomesExport(this.filters)
    // },
    async updatePropertyOptions() {
      const res = await API.getInstance().getSampleGenomePropertyOptions();
      this.propertyOptions = res.property_names;
      this.allColumns = res.property_names.concat(['genomic_profiles', 'proteomic_profiles']).sort();
    },
    async updateRepliconAccessionOptions() {
      const res = await API.getInstance().getRepliconAccessionOptions();
      this.repliconAccessionOptions = res.accessions;
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
      console.log(property)
      return property ? property.value : undefined;
    }
  },
  computed: {
    filters(): FilterGroupRoot {

      const filters = {
        filters: this.getFilterGroupFilters(this.filterGroup)
        // limit: this.perPage,
        // offset: this.firstRow
      };
      return filters as FilterGroupRoot;
    }
  },
  mounted() {
    this.updatePropertyOptions();
    this.updateSymbolOptions();
    this.updateRepliconAccessionOptions();
  },
  components: { GenomicProfileLabel }
}



</script>

<style scoped>
body {
  height: 100vh;
  width: 100vw;
  margin: -0.5em;
  display: flex;
  justify-content: center;
  align-items: center;
  background-color: #adbed3;
}

main {
  height: 97vh;
  width: 98vw;
  display: flex;
  align-items: stretch;
  flex-direction: column;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: var(--shadow);
}

header {
  height: 10%;
  display: flex;
  flex-direction: row;
  align-items: left;
  padding: 20px;
  background-color: var(--primary-color);
}

.menu {
  margin-left: 35%;
}

/* .p-menubar {
    background-color: transparent;
  }
  :deep(.p-menubar .p-menubar-root-list > .p-menuitem > .p-menuitem-content .p-menuitem-link .p-menuitem-text) {
    color: white;
  } */

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

.content {
  width: 100%;
  height: 90%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-evenly;
  background-color: var(--text-color);
}

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
  justify-content: space-evenly;
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
}</style>
