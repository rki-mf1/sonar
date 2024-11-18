<template>
  <div class="filter-and-statistic-panel my-2">
    <div class="filter-left">
      <div style="max-width: 91%;">
        <div class="filter-container">
          <span :style="{ color: 'black', fontWeight: '500' }">Time Range</span>
          <Calendar 
            v-model="startDate"  
            style="flex: auto; min-width: 10rem;" 
            showIcon
            dateFormat="yy-mm-dd" 
            ></Calendar>
          <Calendar 
            v-model="endDate" 
            style="flex: auto;min-width: 10rem;" 
            showIcon
            dateFormat="yy-mm-dd" 
          ></Calendar>
          <Button 
              icon="pi pi-arrow-circle-left"   
              label="&nbsp;Default"
              class="default-calendar-button"
              @click="setDefaultTimeRange">
          </Button>
          <Button 
            v-if="startDate"
            class="ml-2 p-button-sm" 
            @click="removeTimeRange">
          <i class="pi pi-trash" style="font-size: medium"/>
          </Button>
        </div>

        <div class="filter-container" >
          <span style="font-weight: 500">Lineage</span>
          <MultiSelect 
            v-model="lineageFilter.lineageList" 
            display="chip" 
            :options="samplesStore.lineageOptions" 
            filter
            placeholder="Select Lineages" 
            style="width: 68%;"
            :virtualScrollerOptions="{ itemSize: 30 }"
            />

            <div class="switch">
              Include Sublineages?
              <InputSwitch v-model="lineageFilter.includeSublineages" />
            </div>
            <Button 
            v-if="lineageFilter.lineageList.length>0"
            icon="pi pi-trash" 
            class="ml-2 p-button-sm" 
            @click="removeLineageFilter" 
            />
        </div>

        <div class="filter-container">
          <span style="font-weight: 500">DNA/AA Profile</span>
          <InputText
            v-model="profileFilter.value" 
            style="flex: auto" 
            :placeholder="'S:L452R, S:del:143-144, del:21114-21929, T23018G'"
            class="mr-1" 
            />
          <Button 
            @click="removeProfileFilter" 
            icon="pi pi-trash"  
            class="ml-2 p-button-sm" 
            v-if="profileFilter.value"
          />
        </div>

        <div class="button-1">
          <Button 
            icon="pi pi-filter" 
            label="&nbsp;Set Advanced Filters" 
            severity="warning"
            raised
            :style="{ border: isAdvancedFiltersSet ? '4px solid #cf3004' : '' }"
            @click="displayDialogFilter = true" 
        />
            <Button 
              icon="pi pi-database"   
              label="&nbsp;Update sample selection"
              severity="warning"
              raised
              :style="{ border: samplesStore.filtersChanged ? '4px solid #cf3004' : '' }"
              @click="updateSamplesInTableAndFilteredStatistics()">
            </Button>
        </div>
      </div>


      <Dialog v-model:visible="displayDialogFilter" modal header="Set Filters">
        <div style="display: flex; gap: 10px">
          <div>
            <FilterGroup style="width: fit-content; margin: auto" :filterGroup="samplesStore.filterGroup"
              :propertyOptions="samplesStore.propertyOptions"
              :repliconAccessionOptions="samplesStore.repliconAccessionOptions"
              :lineageOptions="samplesStore.lineageOptions" :symbolOptions="samplesStore.symbolOptions"
              :operators="Object.values(DjangoFilterType)" :propertyValueOptions="samplesStore.propertyValueOptions"
              :propertiesDict="samplesStore.propertiesDict"
              v-on:update-property-value-options="samplesStore.updatePropertyValueOptions" />
          </div>
        </div>
        <div v-if="samplesStore.errorMessage" style="margin-top: 20px;">
          <Message severity="error">{{ samplesStore.errorMessage }}</Message>
        </div>
        <div style="display: flex; justify-content: end; gap: 10px">
          <Button 
              icon="pi pi-database"   
              label="&nbsp;Update sample selection"  
              severity="warning"
              raised
              :style="{ border: samplesStore.filtersChanged ? '4px solid #cf3004' : '' }"
              @click="closeAdvancedFilterDialogAndUpdate">
          </Button>
        </div>
        <Button type="button" icon="pi pi-question-circle" label="help" @click="toggleHelp" />
      </Dialog>

      <OverlayPanel ref="advancedFiltersHelp">
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

    <div class="statistics-right">
      <Statistics :filteredCount="samplesStore.filteredCount"></Statistics>
    </div>
  </div>

</template>

<script lang="ts">

import { useSamplesStore } from '@/stores/samples';
import { DjangoFilterType } from '@/util/types'

export default {
  name: "Filters",
  data() {
    const samplesStore = useSamplesStore();
    samplesStore.initializeWatchers();
    
    if (samplesStore.filterGroup.filters.profileFilters.length === 0) {
      samplesStore.filterGroup.filters.profileFilters.push({
        label: 'DNA/AA Profile',
        value: '',
        exclude: false,
      });
    }
    return {
      samplesStore,
      displayDialogFilter: false,
      DjangoFilterType,
    };
  },
  methods: {
    removeTimeRange() {
      if (this.collectionDateFilter) {
        this.collectionDateFilter.value = []
      }
    },
    removeProfileFilter() {
      if (this.samplesStore.filterGroup.filters.profileFilters.length <= 1) {
      this.samplesStore.filterGroup.filters.profileFilters[0] = {
        label: 'DNA/AA Profile',
        value: '',
        exclude: false,
      };
    }
      else {
        this.samplesStore.filterGroup.filters.profileFilters.splice(0, 1);
      }
    },
    removeLineageFilter() {
      this.samplesStore.filterGroup.filters.lineageFilter = {
                                                              label: 'Lineages',
                                                              lineageList: [],
                                                              exclude: false,
                                                              includeSublineages: true,
                                                              isVisible: true,
                                                            };
    },
    closeAdvancedFilterDialogAndUpdate() {
      if (this.samplesStore.filtersChanged) { 
        this.samplesStore.updateSamples();
        this.samplesStore.updateFilteredStatistics();
      }
      this.displayDialogFilter = false;
      this.samplesStore.updateSamples();
      this.samplesStore.updateFilteredStatistics();
    },
    toggleHelp(event: Event) {
      const advancedFiltersHelpRef = this.$refs.advancedFiltersHelp as { toggle?: (event: Event) => void };

      if (advancedFiltersHelpRef && typeof advancedFiltersHelpRef.toggle === 'function') {
        advancedFiltersHelpRef.toggle(event);
      } else {
        console.warn('Help component does not exist');
      }
    },
    updateSamplesInTableAndFilteredStatistics() {
      this.samplesStore.updateFilteredStatistics()
      return this.samplesStore.updateSamples()
    },
    async setDefaultTimeRange(){
      const timeRange = await this.samplesStore.setDefaultTimeRange()
      this.startDate =  timeRange[0] 
      this.endDate = timeRange[1] 
    }
  },
  computed: {
    isAdvancedFiltersSet(): boolean {
      return this.samplesStore.filterGroup.filterGroups.length > 0 // OR-group set
      || this.samplesStore.filterGroup.filters.propertyFilters.length > 1 // other property than collection date for first group set
      || this.samplesStore.filterGroup.filters.repliconFilters.length > 0 // replicon for first group set
      || this.samplesStore.filterGroup.filters.profileFilters.length > 1 // more than one profile filter
      || this.samplesStore.filterGroup.filters.lineageFilter.exclude  // exclude set for first group lineage filter
      || this.samplesStore.filterGroup.filters.profileFilters.some(
        filter => filter.exclude === true) // exclude set for profile filter
    },
    profileFilter() {
      return this.samplesStore.filterGroup.filters.profileFilters[0];
    },
    lineageFilter(){
      return this.samplesStore.filterGroup.filters.lineageFilter;
    },
    collectionDateFilter() {
      return this.samplesStore.filterGroup.filters.propertyFilters.find(
        (filter) => filter.propertyName === 'collection_date'
      );
    },
    startDate: {
      get() {
      if (this.collectionDateFilter && Array.isArray(this.collectionDateFilter.value) &&
          (this.collectionDateFilter.value[0] instanceof Date)) {
        return this.collectionDateFilter.value[0];
      }
      return null;
      },
      set(newValue: Date) {
        if (this.collectionDateFilter && Array.isArray(this.collectionDateFilter.value)) {
          this.collectionDateFilter.value[0] = newValue;
        }
      },
    },
    endDate: {
    get() {
      if (this.collectionDateFilter && Array.isArray(this.collectionDateFilter.value) &&
          (this.collectionDateFilter.value[1] instanceof Date)) {
        return this.collectionDateFilter.value[1];
      }
      return null;
    },

      set(newValue: Date) {
        if (this.collectionDateFilter && Array.isArray(this.collectionDateFilter.value)) {
          this.collectionDateFilter.value[1] = newValue;
        }
      },
    },
  },
  mounted() {
  },
}
</script>

<style scoped>
.filter-and-statistic-panel {
  width: 98%;
  display: flex;
  justify-content: space-between;
  background-color: var(--text-color);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: var(--shadow);
}

.filter-left {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-start; 
  width: 50%;
  margin: 10px;
}

.statistics-right {
  display: flex;
  height: auto; 
  gap: 10px;
  margin-left: auto; 
  align-items: center;  
}

.filter-container {
  display: flex;
  align-items: center; 
  gap: 10px;        
  margin-bottom: 5px;
}

.button-1{
  display: flex;
  justify-content: space-between; 
  align-items: flex-end;      
  margin-bottom: 0px;
}

.switch {
  /* font-variant: small-caps; */
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  font-size: 0.7em;
  margin: 2.5px;
}

.default-calendar-button {
    font-size: 12px; 
    min-width: min-content; 
    padding-top: 1px;
    padding-bottom: 1px;
    padding-left: 4px;
    padding-right: 4px;
    display: flex; 
    flex-direction: column;
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
