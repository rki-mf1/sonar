<template>

<div class="input my-2">
    <div class="input-left">
      <!-- Home View Filters -->
      <div>
        <div class="flex align-items-center" style="gap: 10px; margin-bottom: 10px">
          <span style="font-weight: 500">Time Range</span>
          <Calendar v-model="samplesStore.timeRange" style="flex: auto" showIcon dateFormat="yy-mm-dd" selectionMode="range" :disabled="samplesStore.filterGroupFiltersHasDateFilter" @date-select="samplesStore.updateSamples" />
        </div>

        <div class="flex align-items-center" style="gap: 10px">
          <span style="font-weight: 500">Lineage</span>
          <MultiSelect v-model="samplesStore.lineage" display="chip" :options="lineageOptions" filter placeholder="Select Lineages"
            class="w-full md:w-80" :disabled="samplesStore.filterGroupFiltersHasLineageFilter" @change="samplesStore.updateSamples" />
        </div>
      </div>

      <!-- <Button type="button" icon="pi pi-filter" label="&nbsp;Set Advanced Filters" severity="warning" raised
        :style="{ border: isFiltersSet ? '4px solid #cf3004' : '' }" @click="displayDialogFilter = true" />
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
        <div style="display: flex; justify-content: end; gap: 10px">
          <Button type="button" style="margin-top: 10px" label="OK"
            @click="displayDialogFilter=false; updateSamples"></Button>
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
      </OverlayPanel> -->
    </div>

    <div class="input-right">
      <Statistics :filteredCount="samplesStore.filteredCount"></Statistics>
    </div>
</div>

</template>

<script lang="ts">

import API from '@/api/API';
import { useSamplesStore } from '@/stores/samples';


export default {
    name: "Filters",
    data() {
        return {
            samplesStore: useSamplesStore(), 
            // displayDialogFilter: false,
            // propertyOptions: [],
            // propertiesDict: {}, // to store name and type
            // repliconAccessionOptions: [],
            lineageOptions: [],
            // allColumns: [],
            // propertyValueOptions: {} as {
            //     [key: string]: {
            //     options: string[]
            //     loading: boolean
            //     }
            // }
        }
    },
    methods: {
        // async updatePropertyOptions() {
        //     const res = await API.getInstance().getSampleGenomePropertyOptionsAndTypes()

        //     // Transform the array to an object
        //     this.propertiesDict = res.values.reduce((acc, property) => {
        //         acc[property.name] = property.query_type
        //         return acc
        //     }, {})

        //     this.propertyOptions = Object.keys(this.propertiesDict)
        //     this.allColumns = this.propertyOptions
        //     // this.allColumns = this.propertyOptions.push('genomic_profiles', 'proteomic_profiles').sort();
        // },
        // updatePropertyValueOptions(propertyName: string) {
        //     if (this.propertyValueOptions[propertyName]) return
        //     this.propertyValueOptions[propertyName] = { loading: true, options: [] }
        //     API.getInstance()
        //         .getSampleGenomePropertyValueOptions(propertyName)
        //         .then((res) => {
        //         this.propertyValueOptions[propertyName].options = res.values
        //         this.propertyValueOptions[propertyName].loading = false
        //         })
        // },
        // async updateSymbolOptions() {
        //     const res = await API.getInstance().getGeneSymbolOptions()
        //     this.symbolOptions = res.gene_symbols
        // },
        // async updateRepliconAccessionOptions() {
        //     const res = await API.getInstance().getRepliconAccessionOptions()
        //     this.repliconAccessionOptions = res.accessions
        // },
        async updateLineageOptions() {
            const res = await API.getInstance().getLineageOptions()
            this.lineageOptions = res.lineages
        },
        // toggle(event) {
        //   if (this.$refs.op) {
        //     this.$refs.op.toggle(event); 
        //   }
        // }
    },
    computed: {
    },
    mounted() {
        // this.samplesStore.updateSamples()
        // this.samplesStore.setDefaultTimeRange()
        this.updateLineageOptions()
        // this.updatePropertyOptions()
        // this.updateSymbolOptions()
        // this.updateRepliconAccessionOptions()
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

</style>