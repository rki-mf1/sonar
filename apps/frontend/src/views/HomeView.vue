<template>

  <div class="table-content">
    
    <DataTable 
      :value="samplesStore.samples" 
      style="max-width: 95vw" 
      size="large" 
      dataKey="name" 
      stripedRows 
      :reorderableColumns="true" 
      @columnReorder="onColReorder" 
      scrollable 
      scrollHeight="flex" 
      sortable
      @sort="sortingChanged($event)" 
      selectionMode="single" 
      v-model:selection="selectedRow" 
      @rowSelect="onRowSelect" 
      @rowUnselect="onRowUnselect"
      >
      <template #empty> No Results </template>
      <template #header>
        <div style="display: flex; justify-content: space-between; ">
          <div>
            <Button icon="pi pi-external-link" label="&nbsp;Export" raised @click="displayDialogExport = true"/>
          </div>
          <div style="display: flex; justify-content: flex-end">
            <MultiSelect 
              v-model="selectedColumns" 
              display="chip" 
              :options="samplesStore.propertyOptions" 
              filter 
              placeholder="Select Columns" 
              class="w-full md:w-20rem" 
              @update:modelValue="columnSelection"
              >
              <template #value>
                <div style="margin-top: 5px; margin-left: 5px">
                  {{ selectedColumns.length }} columns selected
                </div>
              </template>
            </MultiSelect>
          </div>
        </div>
      </template>
      <Column field="name" sortable :reorderableColumn="false">
        <template #header>
          <span v-tooltip="metaDataCoverage('name')">Sample Name</span>
        </template>
        <template #body="slotProps" >
          <div class="cell-content" 
            :title="slotProps.data.name">
            {{ slotProps.data.name }}
          </div>
        </template>
      </Column>
      <Column v-for="column in selectedColumns" :sortable="!notSortable.includes(column)" :field="column">
        <template #header>
          <span v-tooltip="metaDataCoverage(column)">{{ column }}</span>
        </template>
        <template #body="slotProps" >
          <div v-if="column === 'genomic_profiles'" class="cell-content" >
            <div>
              <GenomicProfileLabel
                v-for="(variant, index) in Object.keys(slotProps.data.genomic_profiles)"
                :variantString="variant"
                :annotations="slotProps.data.genomic_profiles[variant]"
                :isLast="index === Object.keys(slotProps.data.genomic_profiles).length - 1"
              />
            </div>
          </div>
          <div v-else-if="column === 'proteomic_profiles'" class="cell-content"  >
            <div >
              <GenomicProfileLabel
                v-for="(variant, index) in slotProps.data.proteomic_profiles"
                :variantString="variant"
                :isLast="index === Object.keys(slotProps.data.proteomic_profiles).length - 1"
              />
            </div>
          </div>
          <div v-else-if="column === 'init_upload_date'" class="cell-content" >
            {{ formatDate(slotProps.data.init_upload_date) }}
          </div>

          <div v-else-if="column === 'last_update_date'" class="cell-content" >
            {{ formatDate(slotProps.data.last_update_date) }}
          </div>
          <span v-else class="cell-content">
            {{ findProperty(slotProps.data.properties, column) }}
          </span>
        </template>
      </Column>
      <template #footer>
        <div style="display: flex; justify-content: space-between">
          Total: {{ samplesStore.filteredCount }} Samples
        </div>
        <Paginator
          :totalRecords="samplesStore.filteredCount"
          v-model:rows="samplesStore.perPage"
          :rowsPerPageOptions="[10, 25, 50, 100, 1000, 10000, 100000]"
          v-model:first="samplesStore.firstRow"
          @update:rows="samplesStore.updateSamples()"
        />
      </template>
    </DataTable>

    <Dialog class="flex" v-model:visible="samplesStore.loading" modal :closable="false" header="Loading...">
          <ProgressSpinner class="flex-1 p-3" size="small" v-if="samplesStore.loading" style="color: whitesmoke" />
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
      <SampleDetails :selectedRow="selectedRow" :allColumns="samplesStore.propertyOptions"></SampleDetails>
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
        <Button icon="pi pi-external-link" label="&nbsp;Export" raised :loading="samplesStore.loading" @click="exportFile(exportFormat)" />
      </div>
    </Dialog>
  </div>
  
</template>

<script lang="ts">
import API from '@/api/API'
import { useSamplesStore } from '@/stores/samples';
import { type Property } from '@/util/types'

export default {
  name: 'HomeView',
  data() {
    return {
      samplesStore: useSamplesStore(),
      displayDialogExport: false,
      exportFormat: 'csv',
      selectedRow: null,
      displayDialogRow: false,
      selectedColumns: ['sequencing_reason', 'collection_date', 'lineage', 'lab', 'zip_code', 'genomic_profiles', 'proteomic_profiles'],
      notSortable: ["genomic_profiles", "proteomic_profiles"],
    }
  },
  methods: {
    findProperty(properties: Array<Property>, propertyName: string) {
      const property = properties.find(property => property.name === propertyName);
      return property ? property.value : undefined;
    },
    exportFile(type: string) {
      this.displayDialogExport = false;
      this.samplesStore.loading = true;
      API.getInstance().getSampleGenomesExport(this.samplesStore.filters, this.selectedColumns, this.samplesStore.ordering, type == "xlsx");
      this.samplesStore.loading = false;
    },
    columnSelection(value) {
      this.selectedColumns = value.filter(v => this.samplesStore.propertyOptions.includes(v));
    },
    onColReorder(event) {
     const { dragIndex, dropIndex } = event; 
      // Rearrange columns based on dragIndex and dropIndex
      const reorderedColumns = ['name', ...this.selectedColumns]; // note: 'name' is fixed and cant be reordered
      const movedColumn = reorderedColumns.splice(dragIndex, 1)[0];
      reorderedColumns.splice(dropIndex, 0, movedColumn);

      this.selectedColumns = reorderedColumns.slice(1); // drop 'name' from column list since it is fixed and cant be reordered
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
        this.samplesStore.ordering = sortBy.sortField;
      } else {
        this.samplesStore.ordering = `-${sortBy.sortField}`;
      }
      this.samplesStore.updateSamples();
    },
    formatDate(dateStr: string): string {
      if (!dateStr) return ''; // Handle case where dateStr is undefined or null
      return dateStr.split('T')[0];
    },
    metaDataCoverage(column: string) {
      if (this.samplesStore.filteredCount != 0 && this.samplesStore.filteredStatistics["meta_data_coverage"] != undefined) {
        const coverage = (this.samplesStore.filteredStatistics["meta_data_coverage"][column] / this.samplesStore.filteredCount * 100).toFixed(0);
        return 'Coverage: ' + coverage.toString() + ' %';
      } else {
        return '';
      }
    },
  },
  computed: {
  },
  mounted() {

  },
}
</script>

<style scoped>

.table-content {
  height: 80%;
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

.cell-content {
  height: 2em; 
  flex: 1;
  min-width: 5rem;
  max-width: 20rem;
  overflow-x: auto; 
  white-space: nowrap;
  padding: 0;
  margin: 0;
}

:deep(.p-datatable.p-datatable-lg .p-datatable-tbody  > tr > td ) {
  padding-top: 0.5rem !important;
  padding-right: 0.5rem !important;
  padding-bottom: 0.5rem !important;
  padding-left: 0.5rem!important;
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
