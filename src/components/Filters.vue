<template>
<div class="input my-2">
    <div class="input-left">
      <div style="max-width: 500px;">
        <div class="flex align-items-center" style="gap: 10px; margin-bottom: 10px">
          <span :style="{ color: isTimeRangeInvalid ? 'red' : 'black', fontWeight: '500' }">Time Range</span>
          
          <Calendar v-model="samplesStore.timeRange" style="flex: auto" showIcon dateFormat="yy-mm-dd" selectionMode="range" 
            :disabled="samplesStore.filterGroupFiltersHasDateFilter" :invalid="isTimeRangeInvalid" @date-select="handleDateSelect">
              <template #footer>
                <div class="flex justify-content-center align-items-center" style="width: 100%;">
                  <Button style="font-size: 13px;" icon="pi pi-arrow-circle-left" label="Set Default Time Range" @click="samplesStore.setDefaultTimeRange" />
                </div>
              </template>
          </Calendar>
        </div>

        <div class="flex align-items-center" style="gap: 10px;">
          <span style="font-weight: 500">Lineage</span>
          <MultiSelect v-model="samplesStore.lineage" display="chip" :options="samplesStore.lineageOptions" filter placeholder="Select Lineages"
            class="w-full md:w-80" :disabled="samplesStore.filterGroupFiltersHasLineageFilter" @change="samplesStore.updateSamples" />
          <Button icon="pi pi-times" class="ml-2 p-button-sm" v-if="samplesStore.lineage.length" @click="clearLineaegInput" />
        </div>
      </div>

      <Button type="button" icon="pi pi-filter" label="&nbsp;Set Advanced Filters" severity="warning" raised
        :style="{ border: isFiltersSet ? '4px solid #cf3004' : '' }" @click="displayDialogFilter=true" />
      
      <Dialog v-model:visible="displayDialogFilter" modal header="Set Filters">
        <div style="display: flex; gap: 10px">
          <div>
            <FilterGroup style="width: fit-content; margin: auto" :filterGroup="samplesStore.filterGroup"
              :propertyOptions="samplesStore.propertyOptions" :repliconAccessionOptions="samplesStore.repliconAccessionOptions"
              :lineageOptions="samplesStore.lineageOptions" :symbolOptions="samplesStore.symbolOptions"
              :operators="Object.values(DjangoFilterType)" :propertyValueOptions="samplesStore.propertyValueOptions"
              :propertiesDict="samplesStore.propertiesDict" v-on:update-property-value-options="samplesStore.updatePropertyValueOptions" />
          </div>
        </div>
        <div style="display: flex; justify-content: end; gap: 10px">
          <Button type="button" style="margin-top: 10px" label="OK"
            @click="closeAdvancedFilterDialog()"></Button>
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

    <div class="input-right">
      <Statistics :filteredCount="samplesStore.filteredCount"></Statistics>
    </div>
</div>

</template>

<script lang="ts">

import API from '@/api/API';
import { useSamplesStore } from '@/stores/samples';
import { DjangoFilterType} from '@/util/types'

export default {
    name: "Filters",
    data() {
        return {
            samplesStore: useSamplesStore(), 
            displayDialogFilter: false,
            DjangoFilterType
        }
    },
    methods: {
      handleDateSelect() {
        if (!this.isTimeRangeInvalid) {
          this.samplesStore.updateSamples();
        }
      },
      clearLineaegInput() {
        this.samplesStore.lineage = [];
        this.samplesStore.updateSamples(); 
      },
      closeAdvancedFilterDialog() {
        this.displayDialogFilter = false;
        this.samplesStore.updateSamples()
      },
      toggle(event) {
        if (this.$refs.op) {
          this.$refs.op.toggle(event); 
        }
      }
    },
    computed: {
      isFiltersSet(): boolean {
        return this.samplesStore.filterGroup.filterGroups.length > 0 || Object.values(this.samplesStore.filterGroup.filters).some((filter: any) => Array.isArray(filter) && filter.length > 0)
      },
      isTimeRangeInvalid(): boolean {
        return this.samplesStore.timeRange.includes(null) 
      },
    },
    mounted() {
    }
}
</script>

<style scoped>

.input {
  height: 8rem;
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
  width: 50%;
  display: flex;
  flex-direction: row;
  justify-content: flex-start;
  gap: 20%;
  margin-left: 20px;
  align-items: center;
}

.input-right {
  height: 100%;
  width: 50%;
  display: flex;
  flex-direction: row;
  justify-content: flex-end;
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