<script lang="ts">

  import API from '@/api/API'
  import { useRouter } from 'vue-router';
  import { FilterMatchMode } from 'primevue/api';

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
        // this.pages = res.count / this.perPage
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
          // limit: this.perPage,
          // offset: this.firstRow
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

<template>
  <body>
    <main>
      <header>
        <i class="pi pi-spinner" style="font-size: 3rem; color: var(--text-color); margin-top: 10px; margin-bottom: 10px;"></i> 
        <div style="font-size: 2rem; color: var(--text-color); margin-top: 10px;">ovSonar</div>
        <div class="menu">
            <Menubar :model="menu_items"/>
        </div>
        
        <!-- <v-icon name="pr-spinner" scale="5" animation="float" style="color: white;"/> -->
        <!-- <div style="margin-bottom: 100px;"></div>
        <router-link to="/" class="nav-item">Home</router-link>
        <router-link to="/about" class="nav-item">About</router-link> -->
      </header>
      <div class="content">
        <div class="input">
          <div class="input-left">
            <Button type="button" icon="pi pi-filter" label="&nbsp;Set Filters" severity="warning" raised @click="filter_dialog_visible = true" />
            <Dialog v-model:visible="filter_dialog_visible" modal header="Set Filters">
                <div style="display: flex; gap: 10px;">
                    <!-- <Button type="button" icon="pi pi-filter" label="Add AND Filter" @click=""></Button>
                    <Button type="button" icon="pi pi-filter" label="Add OR Group" @click=""></Button> -->

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

                </div>
                <div style="display: flex; justify-content: end; gap: 10px;">
                    <!-- <Button type="button" label="Cancel" severity="secondary" @click="filter_dialog_visible = false"></Button>
                    <Button type="button" label="Save" @click="filter_dialog_visible = false"></Button> -->
                    <Button type="button" style="margin-top: 10px;" label="OK" @click="filter_dialog_visible = false; updateSamples()"></Button>
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
          <ProgressSpinner size="small" v-if="loading" style="color: whitesmoke" />
          <DataTable :value="samples" ref="dt" style="max-width: 90vw;" size="small" dataKey="name" 
                      stripedRows scrollable scrollHeight="flex" v-model:filters="filters_table" @filter="{ filtered_table_count = $event.filteredValue.length;}">
            <template #empty> No Results </template>
            <template #header>
              <div style="display: flex; justify-content: flex-end;">
                    <IconField iconPosition="left">
                        <InputIcon>
                            <i class="pi pi-search" />
                        </InputIcon>
                        <InputText v-model="filters_table['global'].value" placeholder="Keyword Search" />
                    </IconField>
                </div>
            </template>
            <Column field="name" header="Name"></Column>
            <Column v-for="property in propertyOptions" :header="property">
              <template #body="slotProps">
                <span> {{ findProperty(slotProps.data.properties, property) }} </span>
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
              </template>
            </Column>
            <template #footer> 
              <div style="display: flex; justify-content: space-between;">
                Total: {{ sampleCount }} Samples 
                <!-- Total: {{ filtered_table_count }} Samples  -->
                <Button icon="pi pi-external-link" label="&nbsp;Export Data" raised @click="requestExport()" />
              </div>
            </template>
          </DataTable>
        </div>
      </div>
    </main>
  </body>
</template>

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
    justify-content: center;
    align-items: center;
    background-color: white;
    border-radius: 20px;
    overflow: hidden;
    box-shadow: var(--shadow);
  }

</style>
