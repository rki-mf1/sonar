
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
              @click="filter_dialog_visible = true" />
            <Dialog v-model:visible="filter_dialog_visible" modal header="Set Filters">
              <div style="display: flex; gap: 10px;">
                <!-- <Button type="button" icon="pi pi-filter" label="Add AND Filter" @click=""></Button>
                    <Button type="button" icon="pi pi-filter" label="Add OR Group" @click=""></Button> -->

                <div>
                  <FilterGroup style="width: fit-content; margin: auto" :filterGroup="filterGroup"
                    :propertyOptions="propertyOptions" :repliconAccessionOptions="repliconAccessionOptions"
                    :symbolOptions="symbolOptions" :operators="Object.values(DjangoFilterType)"
                    :propertyValueOptions="propertyValueOptions"
                    v-on:update-property-value-options="updatePropertyValueOptions" />
                </div>

              </div>
              <div style="display: flex; justify-content: end; gap: 10px;">
                <!-- <Button type="button" label="Cancel" severity="secondary" @click="filter_dialog_visible = false"></Button>
                    <Button type="button" label="Save" @click="filter_dialog_visible = false"></Button> -->
                <Button type="button" style="margin-top: 10px;" label="OK"
                  @click="filter_dialog_visible = false; updateSamples()"></Button>
              </div>
            </Dialog>
            <i class="pi pi-arrow-right" style="font-size: 1.5rem; color: var(--grayish);"></i>
            <Button type="button" icon="pi pi-list" label="&nbsp;Get Data" raised @click="updateSamples()" />
          </div>

          <div class="input-right">
            <Statistics></Statistics>
          </div>
        </div>

        <div class="output">
          <div style="height: 50%; width: 100%; display: flex; justify-content: center;">
            <Chart type="bar" :data="chartData" :options="chartOptions" style="width: 80%;" />
          </div>
          <div style="height: 50%; overflow: auto;">
            <ProgressSpinner size="small" v-if="loading" style="color: whitesmoke" />
            <DataTable :value="samples" ref="dt" style="max-width: 90vw;" size="small" dataKey="name" stripedRows
              removableSort scrollable scrollHeight="flex" v-model:filters="filters_table"
              @filter="{ filtered_table_count = $event.filteredValue.length; }">
              <template #empty> No Results </template>
              <template #header>
                <div style="display: flex; justify-content: flex-end;">
                  <MultiSelect v-model="selectedColumns" display="chip" :options="allColumns" filter
                    placeholder="Select Columns" class="w-full md:w-20rem" @update:modelValue="onToggle">
                    <template #value>
                      <div style="margin-top: 5px; margin-left: 5px;">{{ selectedColumns.length }} columns selected</div>
                    </template>
                  </MultiSelect>
                  <IconField iconPosition="left">
                    <InputIcon>
                      <i class="pi pi-search" />
                    </InputIcon>
                    <InputText v-model="filters_table['global'].value" placeholder="Keyword Search"/>
                  </IconField>
                </div>
              </template>
              <Column field="name">
                <template #header>
                  <span v-tooltip="metaDataCoverage('name')">ID</span>
                </template>
              </Column>
              <Column v-for="column in selectedColumns">
                <template #header>
                  <span v-tooltip="metaDataCoverage(column)">{{ column }}</span>
                </template>
                <template #body="slotProps">
                  <div v-if="column === 'genomic_profiles'">
                    <div style="height: 1.5em; width:15rem; overflow-x: auto; white-space: nowrap;">
                      <GenomicProfileLabel v-for="(variant, index) in Object.keys(slotProps.data.genomic_profiles)"
                        :variantString="variant" :annotations="slotProps.data.genomic_profiles[variant]" :isLast="index === Object.keys(slotProps.data.genomic_profiles).length - 1" />
                    </div>
                  </div>
                  <div v-else-if="column === 'proteomic_profiles'">
                    <div style="height: 1.5em; width:15rem; overflow-x: auto; white-space: nowrap;">
                      <GenomicProfileLabel v-for="(variant, index) in slotProps.data.proteomic_profiles"
                        :variantString="variant" :isLast="index === Object.keys(slotProps.data.proteomic_profiles).length - 1" />
                    </div>
                  </div>
                  <span v-else>
                    {{ findProperty(slotProps.data.properties, column) }}
                  </span>
                </template>
              </Column>
              <template #footer>
                <div style="display: flex; justify-content: space-between;">
                  Total: {{ sampleCount }} Samples
                  <!-- Total: {{ filtered_table_count }} Samples  -->
                  <Button icon="pi pi-external-link" label="&nbsp;Export Data" raised @click="exportCSV($event)" />
                  <!-- <Button icon="pi pi-external-link" label="&nbsp;Export Data" raised @click="requestExport()" /> -->
                </div>
              </template>
            </DataTable>
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
          route: '/home'
        },
        {
          label: 'About',
          icon: 'pi pi-star',
          route: '/about'
        }
      ],
      filter_dialog_visible: false,
      filtered_table_count: 0,
      filters_table: {
        global: { value: null, matchMode: FilterMatchMode.CONTAINS }
      },
      // perPage: 10,
      // firstRow: 0,
      // page: 1,
      // pages: 1,
      sampleCount: 0,
      samples: [],
      filteredStatistics: {} as Record<string, number>,
      chartData: {},
      chartOptions: {},
      loading: false,
      propertyOptions: [],
      repliconAccessionOptions: [],
      allColumns: [],
      selectedColumns: ['sequencing_reason', 'collection_date', 'lineage', 'lab', 'zip_code'],
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
      const res = await API.getInstance().getSampleGenomes(this.filters);
      this.filteredStatistics = await API.getInstance().getFilteredStatistics(this.filters);
      this.samples = res.results;
      this.sampleCount = res.count;
      // this.pages = res.count / this.perPage
      this.loading = false;
    },
    metaDataCoverage(column: string) {
      if (this.filteredStatistics["filtered_total_count"] != undefined) {
        const coverage = (this.filteredStatistics[column] / this.filteredStatistics["filtered_total_count"] * 100).toFixed(0);
        return 'Coverage: ' +  coverage.toString() + ' %';
      } else {
          return '';
      }
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
    onToggle(value) {
      this.selectedColumns = this.allColumns.filter(col => value.includes(col));
    },
    setChartData() {
      return {
        labels: ['Q1', 'Q2', 'Q3', 'Q4'],
        datasets: [
          {
            label: 'Sales',
            data: [540, 325, 702, 620],
            backgroundColor: ['rgba(249, 115, 22, 0.2)', 'rgba(6, 182, 212, 0.2)', 'rgb(107, 114, 128, 0.2)', 'rgba(139, 92, 246, 0.2)'],
            borderColor: ['rgb(249, 115, 22)', 'rgb(6, 182, 212)', 'rgb(107, 114, 128)', 'rgb(139, 92, 246)'],
            borderWidth: 1
          }
        ]
      };
    },
    setChartOptions() {
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
      return property ? property.value : undefined;
    },
    async loadPerWeekSampleCount() {
      const res = await API.getInstance().getSamplesPerWeek({});
      const labels = []
      const data = []
      Object.keys(res).forEach(yearWeek => {
        labels.push(yearWeek)
        data.push(res[yearWeek])


      });
      this.chartData = {
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
    }
  },
  computed: {
    filters(): FilterGroupRoot {
      const filters = {
        filters: this.getFilterGroupFilters(this.filterGroup),
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
    this.chartData = this.setChartData();
    this.chartOptions = this.setChartOptions();
    this.loadPerWeekSampleCount();
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
  height: 95vh;
  width: 95vw;
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
  width: 97%;
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

.output {
  height: 70%;
  width: 97%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background-color: white;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: var(--shadow);
}
</style>
