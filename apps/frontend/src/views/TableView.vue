<template>
  <div class="table-content">
    <DataTable
      v-model:selection="selectedRow"
      :value="samplesStore.samples"
      style="max-width: 95vw"
      size="large"
      data-key="name"
      striped-rows
      :reorderable-columns="true"
      scrollable
      scroll-height="flex"
      sortable
      selection-mode="single"
      @column-reorder="onColReorder"
      @sort="sortingChanged($event)"
      @row-select="onRowSelect"
      @row-unselect="onRowUnselect"
    >
      <template #empty> No Results </template>
      <template #header>
        <div style="display: flex; justify-content: space-between">
          <PrimeButton
            icon="pi pi-external-link"
            label="&nbsp;Export"
            severity="warning"
            raised
            @click="displayDialogExport = true"
          />
          <div style="display: flex; justify-content: flex-end">
            <MultiSelect
              v-model="samplesStore.selectedColumns"
              display="chip"
              :options="samplesStore.propertyTableOptions"
              filter
              placeholder="Select Columns"
              class="w-full md:w-20rem"
              @update:model-value="columnSelection"
            >
              <template #value>
                <div style="margin-top: 5px; margin-left: 5px">
                  {{ samplesStore.selectedColumns.length + 1 }} columns selected
                </div>
              </template>
            </MultiSelect>
          </div>
        </div>
      </template>
      <PrimeColumn field="name" sortable :reorderable-column="false">
        <template #header>
          <span>Sample Name</span>
        </template>
        <template #body="slotProps">
          <div class="cell-content-sample-id" :title="slotProps.data.name">
            {{ slotProps.data.name }}
          </div>
        </template>
      </PrimeColumn>
      <PrimeColumn
        v-for="column in samplesStore.selectedColumns"
        :key="column"
        :sortable="!notSortable.includes(column)"
        :field="column"
      >
        <template #header>
          <span>{{ column }}</span>
        </template>
        <template #body="slotProps">
          <div v-if="column === 'genomic_profiles'" class="cell-content">
            <div>
              <GenomicProfileLabel
                v-for="(variant, index) in Object.keys(slotProps.data.genomic_profiles)"
                :key="variant"
                :variant-string="variant"
                :annotations="slotProps.data.genomic_profiles[variant]"
                :is-last="index === Object.keys(slotProps.data.genomic_profiles).length - 1"
              />
            </div>
          </div>
          <div v-else-if="column === 'proteomic_profiles'" class="cell-content">
            <div>
              <GenomicProfileLabel
                v-for="(variant, index) in slotProps.data.proteomic_profiles"
                :key="variant"
                :variant-string="variant"
                :is-last="index === Object.keys(slotProps.data.proteomic_profiles).length - 1"
              />
            </div>
          </div>
          <div v-else-if="column === 'init_upload_date'" class="cell-content">
            {{ formatDate(slotProps.data.init_upload_date) }}
          </div>

          <div v-else-if="column === 'last_update_date'" class="cell-content">
            {{ formatDate(slotProps.data.last_update_date) }}
          </div>
          <span v-else class="cell-content">
            {{ findProperty(slotProps.data.properties, column) }}
          </span>
        </template>
      </PrimeColumn>
      <template #footer>
        <div style="display: flex; justify-content: space-between">
          Total: {{ samplesStore.filteredCount }} Samples
        </div>
        <PrimePaginator
          v-model:rows="samplesStore.perPage"
          v-model:first="samplesStore.firstRow"
          :total-records="samplesStore.filteredCount"
          :rows-per-page-options="[10, 25, 50, 100, 1000, 10000, 100000]"
          @update:rows="samplesStore.updateSamples()"
        />
      </template>
    </DataTable>

    <PrimeDialog
      v-model:visible="samplesStore.loading"
      class="flex"
      modal
      :closable="false"
      header="Loading..."
    >
      <ProgressSpinner
        v-if="samplesStore.loading"
        class="flex-1 p-3"
        size="small"
        style="color: whitesmoke"
      />
    </PrimeDialog>

    <PrimeDialog
      v-model:visible="displayDialogRow"
      modal
      dismissable-mask
      :style="{ width: '60vw' }"
    >
      <template #header>
        <div style="display: flex; align-items: center">
          <strong>Sample Details</strong>
          <div v-if="selectedRow">
            <router-link v-slot="{ href, navigate }" :to="`sample/${selectedRow.name}`" custom>
              <a :href="href" target="_blank" style="margin-left: 8px" @click="navigate">
                <i class="pi pi-external-link"></i>
              </a>
            </router-link>
          </div>
        </div>
      </template>
      <SampleDetails
        :selected-row="selectedRow"
        :all-columns="samplesStore.propertyTableOptions"
      ></SampleDetails>
    </PrimeDialog>

    <PrimeDialog
      v-model:visible="displayDialogExport"
      header="Export Settings"
      modal
      dismissable-mask
      :style="{ width: '25vw' }"
    >
      <div>
        <RadioButton v-model="exportFormat" input-id="exportFormat1" value="csv" />
        <label for="exportFormat1" class="ml-2"> CSV (.csv)</label>
        <br /><br />
        <RadioButton v-model="exportFormat" input-id="exportFormat2" value="xlsx" />
        <label for="exportFormat2" class="ml-2"> Excel (.xlsx)</label>
        <br /><br />
      </div>

      <span><strong>Note: </strong>There is an export limit of maximum XXX samples!</span>

      <div style="display: flex; justify-content: end; gap: 10px; margin-top: 10px">
        <PrimeButton
          icon="pi pi-external-link"
          label="&nbsp;Export"
          severity="warning"
          raised
          :loading="samplesStore.loading"
          @click="exportFile(exportFormat)"
        />
      </div>
    </PrimeDialog>
  </div>

  <PrimeToast ref="exportToast" position="bottom-right" group="br">
    <template #container="{ message, closeCallback }">
      <section class="flex p-3 gap-3" style="border-radius: 10px">
        <i class="pi pi-cloud-download text-primary-500 text-2xl"></i>
        <div class="flex flex-column gap-3 w-full">
          <p class="m-0 font-semibold text-base text-blue">{{ message.summary }}</p>
          <p class="m-0 text-base text-700">{{ message.detail }}</p>
          <div class="flex flex-column gap-2">
            <ProgressBar mode="indeterminate" style="height: 6px"></ProgressBar>
          </div>
        </div>
        <!-- Close Icon (X button) -->
        <PrimeButton
          class="p-toast-close p-link"
          style="position: absolute; top: 5px; right: 5px"
          @click="closeCallback"
        >
          <i class="pi pi-times"></i>
        </PrimeButton>
      </section>
    </template>
  </PrimeToast>
</template>

<script lang="ts">
import API from '@/api/API'
import router from '@/router'
import { decodeDatasetsParam, safeDecodeURIComponent } from '@/util/routeParams'
import { useSamplesStore } from '@/stores/samples'
import { type Property, type RowSelectEvent, type SelectedRowData } from '@/util/types'
import type { DataTableSortEvent } from 'primevue/datatable'

export default {
  name: 'TableView',
  data() {
    return {
      samplesStore: useSamplesStore(),
      displayDialogExport: false,
      exportFormat: 'csv',
      selectedRow: {
        name: '',
        properties: [],
        genomic_profiles: {},
        proteomic_profiles: [],
      } as SelectedRowData,
      displayDialogRow: false,
      notSortable: ['genomic_profiles', 'proteomic_profiles'],
    }
  },
  computed: {
    selectionKey(): string {
      const { accession, dataset = [] } = this.$route.query
      return JSON.stringify({ accession, dataset })
    },
  },
  watch: {
    selectionKey: {
      immediate: true,
      handler() {
        this.applySelectionFromRoute()
      },
    },
  },
  mounted() {
    this.$root.$toastRef = this.$refs.toast ?? null
  },
  methods: {
    // keep table in sync with route params
    applySelectionFromRoute() {
      const accession =
        typeof this.$route.query.accession === 'string'
          ? safeDecodeURIComponent(this.$route.query.accession)
          : null
      if (!accession) {
        console.log('Invalid URL: missing accession parameter.')
        router.replace({ name: 'Home' })
        return
      }
      const datasets = decodeDatasetsParam(this.$route.query.dataset)
      this.samplesStore.setDataset(this.samplesStore.organism, accession, datasets)
      this.loadSamplesAndMetadata()
    },
    loadSamplesAndMetadata() {
      this.samplesStore.updateSamples()
      this.samplesStore
        .updateStatistics()
        .then(() => this.samplesStore.updatePropertyOptions())
        .then(() => this.samplesStore.updateSelectedColumns())
      this.samplesStore.updateFilteredStatistics()
      this.samplesStore.updateLineageOptions()
      this.samplesStore.updateSymbolOptions()
      this.samplesStore.updateRepliconAccessionOptions()
    },
    findProperty(properties: Array<Property>, propertyName: string) {
      const property = properties.find((property) => property.name === propertyName)
      return property ? property.value : undefined
    },
    exportFile(type: string) {
      // Show the progress bar in the toast
      const exportToastRef = this.$refs.exportToast as {
        add: (options: {
          severity: string
          summary: string
          detail: string
          id: number
          group: string
          closable: boolean
        }) => void
      }
      exportToastRef.add({
        severity: 'info',
        summary: 'Exporting...',
        detail: 'Your file is being prepared.',
        id: 1,
        group: 'br',
        closable: true,
      })

      this.displayDialogExport = false
      // this.samplesStore.loading = true;
      API.getInstance()
        .getSampleGenomesExport(
          this.samplesStore.filters,
          this.samplesStore.selectedColumns,
          this.samplesStore.ordering,
          type == 'xlsx',
        )
        .then(() => {
          // Export completed, close the toast
          console.log('complete')
          this.$toast.removeGroup('br')
        })
        .catch(() => {
          // Handle the error, also close the toast in case of error
          this.showToastError('Export failed. Please try again.')
          this.$toast.removeGroup('br')
        })
        .finally(() => {
          // this.samplesStore.loading = false;
        })
      //this.samplesStore.loading = false;
    },
    columnSelection(value: string[]) {
      this.samplesStore.selectedColumns = value.filter((v) =>
        this.samplesStore.propertyTableOptions.includes(v),
      )
    },
    onColReorder(event: { dragIndex: number; dropIndex: number; originalEvent: Event }) {
      const { dragIndex, dropIndex } = event as { dragIndex: number; dropIndex: number }
      // Rearrange columns based on dragIndex and dropIndex
      const reorderedColumns = ['name', ...this.samplesStore.selectedColumns] // note: 'name' is fixed and cant be reordered
      const movedColumn = reorderedColumns.splice(dragIndex, 1)[0]
      reorderedColumns.splice(dropIndex, 0, movedColumn)

      this.samplesStore.selectedColumns = reorderedColumns.slice(1) // drop 'name' from column list since it is fixed and cant be reordered
    },
    onRowSelect(event: RowSelectEvent<SelectedRowData>) {
      this.selectedRow = event.data
      this.displayDialogRow = true
    },
    onRowUnselect() {
      this.selectedRow = {
        name: '',
        properties: [],
        genomic_profiles: {},
        proteomic_profiles: [],
      }
      this.displayDialogRow = false
    },
    sortingChanged(sortBy: DataTableSortEvent) {
      if (sortBy.sortOrder) {
        if (sortBy.sortOrder > 0 && typeof sortBy.sortField === 'string') {
          this.samplesStore.ordering = sortBy.sortField
        } else {
          this.samplesStore.ordering = `-${sortBy.sortField}`
        }
        this.samplesStore.updateSamples()
      }
    },
    formatDate(dateStr: string): string {
      if (!dateStr) return '' // Handle case where dateStr is undefined or null
      return dateStr.split('T')[0]
    },
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

.cell-content-sample-id {
  height: 2em;
  flex: 1;
  min-width: 5rem;
  max-width: 20rem;
  overflow-x: auto;
  white-space: nowrap;
  padding: 0;
  margin: 0;
  text-align: right;
  text-overflow: ellipsis;
  direction: rtl;
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

:deep(.p-datatable.p-datatable-lg .p-datatable-tbody > tr > td) {
  padding-top: 0.5rem !important;
  padding-right: 0.5rem !important;
  padding-bottom: 0.5rem !important;
  padding-left: 0.5rem !important;
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
