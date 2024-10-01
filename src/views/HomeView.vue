<template>
  <div class="input grid m-1">
    <div class="col">
      <!-- Home View Filters -->
      <div class="grid">
        <div class="col">
          <div class="flex align-items-center" style="gap: 10px; margin-bottom: 10px;">
            <span style="font-weight: 500;">Time Range</span>
            <Calendar v-model="timeRange" style="flex: auto" showIcon dateFormat="yy-mm-dd" selectionMode="range"
              @date-select="updateSamples" />
          </div>

          <div class="flex align-items-center" style="gap: 10px">
            <span style="font-weight: 500;">Lineage</span>
            <MultiSelect v-model="lineage" display="chip" :options="lineageOptions" filter placeholder="Select Lineages"
              class="w-full md:w-80" @change="updateSamples" />
          </div>
        </div>
        <div class="col">
          <Button type="button" icon="pi pi-filter" label="&nbsp;Set Advanced Filters" severity="warning" raised
            :style="{ border: isFiltersSet ? '4px solid #cf3004' : '' }" @click="displayDialogFilter = true" />
        </div>
      </div>
      <Dialog v-model:visible="displayDialogFilter" modal header="Set Filters">
        <div style="display: flex; gap: 10px">
          <div>
            <FilterGroup style="width: fit-content; margin: auto" :filterGroup="filterGroup"
              :propertyOptions="propertyOptions" :repliconAccessionOptions="repliconAccessionOptions"
              :lineageOptions="lineageOptions" :symbolOptions="symbolOptions"
              :operators="Object.values(DjangoFilterType)" :propertyValueOptions="propertyValueOptions"
              :propertiesDict="propertiesDict" v-on:update-property-value-options="updatePropertyValueOptions" />
          </div>
        </div>
        <div v-if="errorMessage" style="margin-top: 20px;">
          <Message severity="error">{{ errorMessage }}</Message>
        </div>
        <div style="display: flex; justify-content: end; gap: 10px;">
          <Button type="button" style="margin-top: 10px;" label="OK"
            @click="displayDialogFilter = false; updateSamples()"></Button>
        </div>
        <Button type="button" icon="pi pi-question-circle" label="help" @click="toggle" />
      </Dialog>
      <OverlayPanel ref="op">
        <div class="flex flex-column gap-3 w-25rem">
          <div>
            <span class="font-medium text-900 block mb-2">Example of Input</span>
            <Accordion :activeIndex="0">
              <AccordionTab header="Property: Date">
                <p class="m-0">
                  We let users select a range of dates where first date is the start of the range
                  and second date is the end.
                  <Chip label="2021-12-30 - 2023-01-18" />
                </p>
              </AccordionTab>
              <AccordionTab header="Operator: exact">
                <p class="m-0">
                  exact = "exact match"
                  <br />
                  This operator filters values that exactly match the given input.
                  <br />
                  Example: A ID(name) filter with
                  <Chip label="ID-001" /> will return records with this exact ID.
                </p>
              </AccordionTab>
              <AccordionTab header="Operator: contain">
                <p class="m-0">
                  contains = "substring match"
                  <br />
                  Filters records that contain the input value as a substring.
                  <br />
                  Example: A name filter with
                  <Chip label="John" /> will return names like "Johnathan" or "Johnny."
                </p>
              </AccordionTab>
              <AccordionTab header="Operator: gt">
                <p class="m-0">
                  gt = "greater than" <br />
                  Example:
                  <Chip label="10" /> will filter records where the value is greater than 10.
                </p>
              </AccordionTab>
              <AccordionTab header="Operator: gte">
                <p class="m-0">
                  gte = "greater than or equal" <br />
                  Example:
                  <Chip label="15" /> will filter records where the value is greater than or equal
                  to 15.
                </p>
              </AccordionTab>
              <AccordionTab header="Operator: lt">
                <p class="m-0">
                  lt = "less than" <br />
                  Example:
                  <Chip label="20" /> will filter records where the value is less than 20.
                </p>
              </AccordionTab>
              <AccordionTab header="Operator: lte">
                <p class="m-0">
                  lte = "less than or equal" <br />
                  Example:
                  <Chip label="25" /> will filter records where the value is less than or equal to
                  25.
                </p>
              </AccordionTab>
              <AccordionTab header="Operator: range">
                <p class="m-0">
                  range = "value between two numbers" <br />
                  Example value input:
                  <Chip label="(1, 5)" /> <br />
                  This means the value starts from 1 and goes up to 5, inclusive.
                </p>
              </AccordionTab>
              <AccordionTab header="Operator: regex">
                <p class="m-0">
                  regex = "matches regular expression" <br />
                  Example:
                  <Chip label="^IMS-101" /> will filter records where the value starts with
                  'IMS-101'. <br />
                  For more regex expressions, please visit
                  <a href="https://regex101.com/" target="_blank">this link</a>.
                </p>
              </AccordionTab>
            </Accordion>
          </div>
        </div>
      </OverlayPanel>
    </div>

    <div class="col input-right">
      <Statistics :filteredCount="filteredCount"></Statistics>
    </div>
  </div>

  <div class="output_box">
    <div class="output mb-2">
      <div style="height: 100%; overflow: auto">
        <Dialog class="flex" v-model:visible="loading" modal :closable="false" header="Loading...">
          <ProgressSpinner class="flex-1 p-3" size="small" v-if="loading" style="color: whitesmoke" />
        </Dialog>

        <Dialog v-model:visible="displayDialogRow" modal dismissableMask :style="{ width: '60vw' }">
          <template #header>
            <div style="display: flex; align-items: center">
              <strong>Sample Details</strong>
              <router-link v-slot="{ href, navigate }" :to="`sample/${selectedRow.name}`" custom>
                <a :href="href" target="_blank" @click="navigate" style="margin-left: 8px">
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
            <br /><br />
            <RadioButton v-model="exportFormat" inputId="exportFormat2" value="xlsx" />
            <label for="exportFormat2" class="ml-2"> Excel (.xlsx)</label>
            <br /><br />
          </div>

          <span><strong>Note: </strong>There is an export limit of maximum XXX samples!</span>

          <div style="display: flex; justify-content: end; gap: 10px; margin-top: 10px">
            <Button icon="pi pi-external-link" label="&nbsp;Export" raised @click="exportFile(exportFormat)" />
          </div>
        </Dialog>

        <DataTable :value="samples" ref="dt" style="max-width: 90vw" size="large" dataKey="name" stripedRows scrollable
          scrollHeight="flex" sortable @sort="sortingChanged($event)" v-model:selection="selectedRow"
          selectionMode="single" @rowSelect="onRowSelect" @rowUnselect="onRowUnselect">
          <template #empty> No Results </template>
          <template #header>
            <div style="display: flex; justify-content: space-between">
              <div>
                <Button icon="pi pi-external-link" label="&nbsp;Export" raised @click="displayDialogExport = true" />
              </div>
              <div style="display: flex; justify-content: flex-end">
                <MultiSelect v-model="selectedColumns" display="chip" :options="allColumns" filter
                  placeholder="Select Columns" class="w-full md:w-20rem" @update:modelValue="columnSelection">
                  <template #value>
                    <div style="margin-top: 5px; margin-left: 5px">
                      {{ selectedColumns.length }} columns selected
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
              <div style="
                  height: 1.5em;
                  width: 9rem;
                  text-overflow: ellipsis;
                  overflow: hidden;
                  white-space: nowrap;
                  direction: rtl;
                " :title="slotProps.data.name">
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
                <div style="height: 2.5em; width: 20rem; overflow-x: auto; white-space: nowrap">
                  <GenomicProfileLabel v-for="(variant, index) in Object.keys(slotProps.data.genomic_profiles)"
                    :variantString="variant" :annotations="slotProps.data.genomic_profiles[variant]"
                    :isLast="index === Object.keys(slotProps.data.genomic_profiles).length - 1" />
                </div>
              </div>
              <div v-else-if="column === 'proteomic_profiles'">
                <div style="height: 2.5em; width: 20rem; overflow-x: auto; white-space: nowrap">
                  <GenomicProfileLabel v-for="(variant, index) in slotProps.data.proteomic_profiles"
                    :variantString="variant"
                    :isLast="index === Object.keys(slotProps.data.proteomic_profiles).length - 1" />
                </div>
              </div>
              <div v-else-if="column === 'init_upload_date'">
                {{ formatDate(slotProps.data.init_upload_date) }}
              </div>

              <div v-else-if="column === 'last_update_date'">
                {{ formatDate(slotProps.data.last_update_date) }}
              </div>
              <span v-else>
                {{ findProperty(slotProps.data.properties, column) }}
              </span>
            </template>
          </Column>
          <template #footer>
            <div style="display: flex; justify-content: space-between">
              Total: {{ filteredCount }} Samples
            </div>
            <Paginator :totalRecords="filteredCount" v-model:rows="perPage"
              :rowsPerPageOptions="[10, 25, 50, 100, 1000, 10000, 100000]" v-model:first="firstRow"
              @update:rows="updateSamples()" />
          </template>
        </DataTable>
      </div>
      <div style="height: 100%; width: 30%; display: flex; justify-content: center">
        <Chart type="bar" :data="chartData()" :options="chartOptions()" style="width: 80%" />
      </div>
    </div>

    <Toast ref="toast" />
  </div>
</template>

<script lang="ts">

import API from '@/api/API'
import { ref } from "vue";
import {
  type FilterGroup,
  type LineageFilter,
  type PropertyFilter,
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
      IUPAC_CODES: {
        nt: {
          A: new Set("A"),
          C: new Set("C"),
          G: new Set("G"),
          T: new Set("T"),
          R: new Set("AGR"),
          Y: new Set("CTY"),
          S: new Set("GCS"),
          W: new Set("ATW"),
          K: new Set("GTK"),
          M: new Set("ACM"),
          B: new Set("CGTB"),
          D: new Set("AGTD"),
          H: new Set("ACTH"),
          V: new Set("ACGV"),
          N: new Set("ACGTRYSWKMBDHVN"),
          n: new Set("N"),
        },
        aa: {
          A: new Set("A"),
          R: new Set("R"),
          N: new Set("N"),
          D: new Set("D"),
          C: new Set("C"),
          Q: new Set("Q"),
          E: new Set("E"),
          G: new Set("G"),
          H: new Set("H"),
          I: new Set("I"),
          L: new Set("L"),
          K: new Set("K"),
          M: new Set("M"),
          F: new Set("F"),
          P: new Set("P"),
          S: new Set("S"),
          T: new Set("T"),
          W: new Set("W"),
          Y: new Set("Y"),
          V: new Set("V"),
          U: new Set("U"),
          O: new Set("O"),
          B: new Set("DNB"),
          Z: new Set("EQZ"),
          J: new Set("ILJ"),
          Φ: new Set("VILFWYMΦ"),
          Ω: new Set("FWYHΩ"),
          Ψ: new Set("VILMΨ"),
          π: new Set("PGASπ"),
          ζ: new Set("STHNQEDKRζ"),
          "+": new Set("KRH+"),
          "-": new Set("DE-"),
          X: new Set("ARNDCQEGHILKMFPSTWYVUOBZJΦΩΨπζ+-X"),
          x: new Set("X"),
        },
      },
      regexes: {
        snv: /^(\^*)(|[^:]+:)?([^:]+:)?([A-Z]+)([0-9]+)(=?[A-Zxn]+)$/,
        del: /^(\^*)(|[^:]+:)?([^:]+:)?del:(=?[0-9]+)(|-=?[0-9]+)?$/
      },
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
      propertiesDict: {}, // to store name and type
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
      lineage: '',
      timeRange: [] as Date[],
      symbolOptions: [],
      filterGroup: {
        filterGroups: [],
        filters: { propertyFilters: [], profileFilters: [], repliconFilters: [], lineageFilters: [] }
      } as FilterGroup,
      DjangoFilterType,
      errorMessage: '',
    };
  },
  setup() {
    // Create the ref for the OverlayPanel
    const op = ref(null);

    // Toggle function to open/close the overlay
    const toggle = (event) => {
      if (op.value) {
        op.value.toggle(event);  // Use the ref's toggle method if op is available
      }
    };

    return {
      op,
      toggle,
    };
  },
  methods: {
    async updateSamples() {
      this.errorMessage = '';
      this.loading = true;
      const params = {
        limit: this.perPage,
        offset: this.firstRow,
        ordering: this.ordering
      }
      this.samples = (await API.getInstance().getSampleGenomes(this.filters, params)).results;
      this.filteredStatistics = await API.getInstance().getFilteredStatistics(this.filters);
      this.filteredCount = this.filteredStatistics["filtered_total_count"];
      this.isFiltersSet = this.filterGroup.filterGroups.length > 0 || Object.values(this.filterGroup.filters).some((filter: any) => Array.isArray(filter) && filter.length > 0);
      this.loading = false;
    },
    async setDefaultTimeRange() {
      const statistics = await API.getInstance().getSampleStatistics()
      this.timeRange = [new Date(statistics.first_sample_date), new Date(statistics.latest_sample_date)]
    },
    formatDate(dateStr: string): string {
      if (!dateStr) return ''; // Handle case where dateStr is undefined or null
      return dateStr.split('T')[0];
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
      API.getInstance().getSampleGenomesExport(this.filters, this.selectedColumns, this.ordering, type == "xlsx");
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
      const samples_per_week = this.filteredStatistics ? this.filteredStatistics["samples_per_week"] : {};
      const labels = [];
      const data = [];

      if (samples_per_week && Object.keys(samples_per_week).length > 0) {
        Object.keys(samples_per_week).forEach(key => {
          labels.push(key);
          data.push(samples_per_week[key]);
        });
      } else {
        // Return an empty chart structure
        return {
          labels: ['No data available'],  // A label to indicate no data
          datasets: [
            {
              label: 'Samples',
              data: [],  // No data points
              backgroundColor: 'rgba(249, 115, 22, 0.2)',
              borderColor: 'rgb(249, 115, 22)',
              borderWidth: 1
            }
          ]
        };
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
      };
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
    // async updatePropertyOptions() {
    //   const res = await API.getInstance().getSampleGenomePropertyOptions();
    //   this.propertyOptions = res.property_names;
    //   this.allColumns = res.property_names.concat(['genomic_profiles', 'proteomic_profiles']).sort();
    // },
    async updatePropertyOptions() {
      const res = await API.getInstance().getSampleGenomePropertyOptionsAndTypes();

      // Transform the array to an object
      this.propertiesDict = res.values.reduce((acc, property) => {
        acc[property.name] = property.query_type;
        return acc;
      }, {});

      this.propertyOptions = Object.keys(this.propertiesDict);
      this.allColumns = this.propertyOptions;
      // this.allColumns = this.propertyOptions.push('genomic_profiles', 'proteomic_profiles').sort();
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
      // Parse the first date
      data[0] = new Date(Date.parse(data[0].toString()));
      //  format the date according to your local timezone instead of UTC.
      const formatDateToLocal = (date) => {
        return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
          .toISOString()
          .split('T')[0];
      };

      // Check if there's a second date
      if (data[1]) {
        data[1] = new Date(Date.parse(data[1].toString()));
        const formatted = [formatDateToLocal(data[0]), formatDateToLocal(data[1])];
        return formatted;
      } else {
        // If there's no second date, assume a range of one day?
        const nextDay = new Date(Date.parse(data[0]) + 1000 * 60 * 60 * 24);
        return [formatDateToLocal(data[0]), formatDateToLocal(nextDay)];
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

        if (filter['label'] == 'Label') {
          // matches any sequence of spaces (\s), commas (,)
          const mutations = filter['value'].split(/[\s,]+/).filter(Boolean);
          const profileQuery = this.createProfileQuery(mutations, filter['exclude']);
          summary.andFilter.push(profileQuery);

        } else {
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
    },
    createProfileQuery(profiles: [], exclude: boolean) {
      const andFilter = { andFilter: [] };
      profiles.forEach(mutation => {
        const query = this.defineProfile(mutation, exclude);
        if (Object.keys(query).length > 0) {
          andFilter.andFilter.push(query);
        }
      });

      return andFilter;
    },
    defineProfile(mutation: string, exclude: boolean) {
      let query = { label: "" };
      let match = null;

      for (const [mutationType, regex] of Object.entries(this.regexes)) {
        match = mutation.match(regex);
        if (match) {
          const geneName = match[2] ? match[2].slice(0, -1) : null;
          if (mutationType === "snv") {
            const alt = match[6];

            for (let x of alt) {
              if (!this.IUPAC_CODES.aa.hasOwnProperty(x) && !this.IUPAC_CODES.nt.hasOwnProperty(x)) {
                this.errorMessage = (`Invalid alternate allele notation '${alt}'.`);
                // this.showToastError(this.errorMessage);
                return {};
              }
            }
            if (geneName) {
              query.alt_aa = alt;
              query.ref_aa = match[4];
              query.ref_pos = match[5];
              query.protein_symbol = geneName;
              query.label = alt.length === 1 ? "SNP AA" : "Ins AA";
            } else {
              query.alt_nuc = alt;
              query.ref_nuc = match[4];
              query.ref_pos = match[5];
              query.label = alt.length === 1 ? "SNP Nt" : "Ins Nt";
            }
          } else if (mutationType === "del") {
            query.first_deleted = match[4];
            query.last_deleted = match[5]?.slice(1) || "";

            if (geneName) {
              query.protein_symbol = geneName;
              query.label = "Del AA";
            } else {
              query.label = "Del Nt";
            }
          }

          query.exclude = exclude;
          break;
        }
      }

      if (!match) {
        this.errorMessage = (`Invalid mutation notation '${mutation}'.`);
        // this.showToastError(this.errorMessage)
        return {};
      }

      return query;
    },
    showToastError(message: string) {

      this.$refs.toast.add({
        severity: 'error',
        summary: 'Error',
        detail: message,
        life: 10000
      });
    }
  },
  computed: {
    filters(): FilterGroupRoot {

      const filters = {
        filters: this.getFilterGroupFilters(this.filterGroup),
      };
      if (!filters.filters?.andFilter) {
        filters.filters.andFilter = []
      }

      if (this.timeRange[0] && this.timeRange[1]) {
        filters.filters.andFilter.push(
          {
            label: 'Property',
            property_name: 'collection_date',
            filter_type: "range",
            value: `${this.timeRange[0].toLocaleDateString('en-CA')},${this.timeRange[1].toLocaleDateString('en-CA')}` // formatted as "yyyy-mm-dd,yyyy-mm-dd"
          }
        )
      }

      if (this.lineage) {
        filters.filters.andFilter.push(
          {
            label: 'Sublineages',
            lineage: this.lineage,
            exclude: false
          }
        )
      }

      return filters as FilterGroupRoot;
    }

  },
  mounted() {
    this.updateSamples();
    this.setDefaultTimeRange();
    this.updatePropertyOptions();
    this.updateSymbolOptions();
    this.updateRepliconAccessionOptions();
    this.updateLineageOptions();
  }
}
</script>

<style scoped>
.input {

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
  background: var(--primary-color-lighter);
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
