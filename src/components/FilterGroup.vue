<script lang="ts">

import API from '@/api/API';
import {
  type FilterGroup,
  type ClassicFilter,
  type PropertyFilter,
  type SNPProfileNtFilter,
  type SNPProfileAAFilter,
  type DelProfileNtFilter,
  type DelProfileAAFilter,
  type InsProfileNtFilter,
  type InsProfileAAFilter,
  type ProfileFilter,
  type RepliconFilter,
  type LineageFilter,
  DjangoFilterType,
  StringDjangoFilterType,
  DateDjangoFilterType,
} from '@/util/types'

import type { MenuItem } from 'primevue/menuitem'

export default {
  name: 'FilterGroup',
  props: {
    filterGroup: {
      type: Object as () => FilterGroup,
      required: true
    },
    propertyOptions: {
      type: Array as () => string[],
      required: true
    },
    symbolOptions: {
      type: Array as () => string[],
      required: true
    },
    repliconAccessionOptions: {
      type: Array as () => string[],
      required: true
    },
    lineageOptions: {
      type: Array as () => string[],
      required: true
    },
    operators: {
      type: Array as () => string[],
      required: true
    },
    propertyValueOptions: {
      type: Object as () => { [key: string]: { options: string[]; loading: boolean } },
      required: true
    },
    propertiesDict : Object
  },
  data() {
    return {
      localOperators: [...this.operators],
      fetchOptionsProperties: ['genome_completeness',
      'sequencing_tech',
      'sequencing_reason', 
      'zip_code',
      'country',
      'host'],
      ClassicFilter: {
        label: '"Label"',
        value: '',
        exclude: false
      } as ClassicFilter,
      PropertyFilter: {
        label: 'Property',
        value: '',
        propertyName: '',
        filterType: null
      } as PropertyFilter,
      RepliconFilter: {
        label: 'Replicon',
        accession: '',
        exclude: false
      } as RepliconFilter,
      LineageFilter: {
        label: 'Sublineages',
        lineage: '',
        exclude: false
      } as LineageFilter,
      profileFilterTypes: {
        SNPProfileNt: {
          label: 'SNP Nt',
          refNuc: '',
          refPos: '',
          altNuc: '',
          exclude: false
        } as SNPProfileNtFilter,
        SNPProfileAA: {
          label: 'SNP AA',
          proteinSymbol: '',
          refAA: '',
          refPos: '',
          altAA: '',
          exclude: false
        } as SNPProfileAAFilter,
        DelProfileNt: {
          label: 'Del Nt',
          firstDeleted: '',
          lastDeleted: '',
          exclude: false
        } as DelProfileNtFilter,
        DelProfileAA: {
          label: 'Del AA',
          proteinSymbol: '',
          firstDeleted: '',
          lastDeleted: '',
          exclude: false
        } as DelProfileAAFilter,
        InsProfileNt: {
          label: 'Ins Nt',
          refNuc: '',
          refPos: '',
          altNuc: '',
          exclude: false
        } as InsProfileNtFilter,
        InsProfileAA: {
          label: 'Ins AA',
          proteinSymbol: '',
          refAA: '',
          refPos: '',
          altAA: '',
          exclude: false
        } as InsProfileAAFilter
      } as { [key: string]: ProfileFilter },
      // to store the earliest and latest dates for each property.
      dateRanges: {} as { [key: string]: { earliest: string; latest: string } },
    }
  },
  computed: {
    sliderValue: {
        get() {
          // Convert filter.value to a number for the Slider
          const numericValue = parseFloat(this.filter?.value);
          return isNaN(numericValue) ? 0 : numericValue;
        },
        set(newValue) {
          // Convert the Slider value back to a string for filter.value
          return newValue.toString();
        },
    },
    filterTypeMethods(): MenuItem[] {
      const menuItems = []
      for (const [key, value] of Object.entries(this.profileFilterTypes)) {
        menuItems.push({
          label: key,
          icon: 'pi pi-plus',
          command: () => {
            this.filterGroup.filters.profileFilters.push({ ...value })
          }
        })
      }
      menuItems.push({
        label: 'PropertyFilter',
        icon: 'pi pi-plus',
        command: () => {
          this.filterGroup.filters.propertyFilters.push({ ...this.PropertyFilter })
        }
      })
      menuItems.push({
        label: 'RepliconFilter',
        icon: 'pi pi-plus',
        command: () => {
          this.filterGroup.filters.repliconFilters.push({ ...this.RepliconFilter })
        }
      })
      menuItems.push({
        label: 'SubLineageFilter',
        icon: 'pi pi-plus',
        command: () => {
          this.filterGroup.filters.lineageFilters.push({ ...this.LineageFilter })
        }
      })
      return menuItems
    },
    cantAddOrGroup(): boolean {
      return (
          this.filterGroup.filters.propertyFilters.length +
          this.filterGroup.filters.profileFilters.length +
          this.filterGroup.filters.repliconFilters.length + 
          this.filterGroup.filters.lineageFilters.length ==
        0
      )
    }
  },
  methods: {
    async get_defaults_earliest_latest_collect_date(propertyName: string) {
      // Check if the property already has a stored date range
      if (this.dateRanges[propertyName]) {
        return this.dateRanges[propertyName]; // Return the cached date range
      }

      // Fetch the date range if not already cached
      const response = await API.getInstance().getSampleGenomePropertyValueOptions(propertyName);
      const dateArray = response.values;

      // Sort dates and store the earliest and latest dates in the dictionary
      if (dateArray) {
        const sortedDates = dateArray.sort((a: string, b: string) => new Date(a).getTime() - new Date(b).getTime());
        this.dateRanges[propertyName] = {
          earliest: sortedDates[0],
          latest: sortedDates[sortedDates.length - 1],
        };
      }

      console.log(`Earliest Date for ${propertyName}:`, this.dateRanges[propertyName]?.earliest);
      console.log(`Latest Date for ${propertyName}:`, this.dateRanges[propertyName]?.latest);

      return this.dateRanges[propertyName];
    },
    addOrFilterGroup() {
      this.filterGroup.filterGroups.push({
        filterGroups: [],
        filters: { propertyFilters: [], profileFilters: [], repliconFilters: [], lineageFilters: []}
      })
    },
    markGroup(group: FilterGroup, mark: boolean) {
      group.marked = mark
    },
    addClassicFilter() {
      this.filterGroup.filters.profileFilters.push({ ...this.ClassicFilter })
    },
    async updatePropertyValueOptions(filter: PropertyFilter) {
      if (this.fetchOptionsProperties.includes(filter.propertyName)) {
        this.$emit('update-property-value-options', filter.propertyName)
      }

      this.initializeOperators(filter);

      // If the property is a date, set the default value to the date range
      if (filter.propertyName?.includes('date')) {
        const dateRange = await this.get_defaults_earliest_latest_collect_date(filter.propertyName);
        if (dateRange) {
          filter.value = [new Date(dateRange.earliest), new Date(dateRange.latest)];
        }
      }else{
        // default 
          filter.value = ""
      }
    },
    initializeOperators(filter: { fetchOptions?: boolean; label?: string; value?: string; propertyName: any; filterType?: DjangoFilterType | null; }) {
      console.log("initializeOperators: " + filter.propertyName)
      const propertyType = this.propertiesDict[filter.propertyName];
      let newOperators = [];

      if (propertyType === 'value_varchar') {
        newOperators = Object.values(StringDjangoFilterType);
      } 
      else if(propertyType === 'value_date'){
        newOperators = Object.values(DateDjangoFilterType);
      }else {
        newOperators = Object.values(DjangoFilterType);
      }
      this.localOperators = newOperators;
      filter.filterType = newOperators[0]
    },
  },
  watch: {

  },
  mounted() {
    // Initialize the operators array when the component is mounted
    // also use when the set filter dialog open again to prevent lost of filter type
    this.filterGroup.filters.propertyFilters.forEach((filter) => {
      this.initializeOperators(filter);
    });
    
  },
}
</script>


<template>
    <div :class="filterGroup.marked ? 'filter-group marked' : 'filter-group'">
      <!-- Property Filters -->
      <div v-for="filter in filterGroup.filters?.propertyFilters" class="single-filter">
        <span class="filter-label">Property</span>
        <Dropdown :options="propertyOptions" v-model="filter.propertyName"
        style="flex: auto"
        @change="updatePropertyValueOptions(filter)" />
        <span class="filter-label">Operator</span>
        <Dropdown :options="localOperators" v-model="filter.filterType" class="mr-2" 
        style="flex: auto" />
        
        <Calendar v-if="filter.propertyName?.includes('date')" 
        v-model="filter.value" style="flex: auto"
        showIcon
        dateFormat="yy-mm-dd" selectionMode="range"/> 
        <Dropdown v-else-if="fetchOptionsProperties.includes(filter.propertyName)"
        :options="propertyValueOptions[filter.propertyName]?.options"
        :loading="propertyValueOptions[filter.propertyName]?.loading"
        v-model="filter.value" style="flex: auto"
        filter >
        </Dropdown>
        <InputText v-else v-model="filter.value" style="flex: auto" />

        <Button type="button" raised size="small" @click="
          filterGroup.filters?.propertyFilters?.splice(
            filterGroup.filters?.propertyFilters?.indexOf(filter),
            1
          )
          " icon="pi pi-trash" label="" severity="danger">
        </Button>
      </div>
      <!-- when click Add AND Filter -->
      <div v-for="filter in filterGroup.filters?.profileFilters" class="single-filter">
        <span class="filter-label">{{ filter.label }}</span>
        <div v-for="key in Object.keys(filter) as Array<keyof ProfileFilter>">
          <div v-if="key == 'exclude'" class="exclude-switch">
            Exclude?
            <InputSwitch v-model="filter[key]"/>
          </div>
          <Dropdown v-else-if="['proteinSymbol', 'geneSymbol'].includes(key)" :placeholder="key" :options="symbolOptions"
            v-model="filter[key]" style="flex: auto" />
          <InputText v-else-if="key != 'label'" v-model="filter[key]" style="flex: auto" :placeholder="key" />
        </div> 
        <Button type="button" severity="danger" size="small" @click="
          filterGroup.filters?.profileFilters?.splice(
            filterGroup.filters?.profileFilters?.indexOf(filter),
            1
          )
          " icon="pi pi-trash">
          <i class="pi pi-trash"></i>
        </Button>
      </div>
      <!-- Replicon Filter -->
      <div v-for="filter in filterGroup.filters?.repliconFilters" class="single-filter">
        <div class="flex flex-column">
          <div class="flex align-items-center ">
            <lable class="filter-label">Replicon</lable>
        <Dropdown :options="repliconAccessionOptions" v-model="filter.accession" style="flex: auto" />
        <div class="exclude-switch">
          Exclude?
          <InputSwitch v-model="filter.exclude" />
        </div>
        <Button type="button"  size="small" @click="
          filterGroup.filters?.repliconFilters?.splice(
            filterGroup.filters?.repliconFilters?.indexOf(filter),
            1
          )
          "  icon="pi pi-trash">

        </Button>
          </div>

        </div>

        
      </div>
      <!-- Lineage Filter -->
      <div v-for="filter in filterGroup.filters?.lineageFilters" class="single-filter">
        <div class="flex flex-column">
          <div class="flex align-items-center ">
            <span class="filter-label">Lineage</span>
            <!-- <InputText v-model="filter.lineage" style="flex: auto"/> -->
            <Dropdown :options="lineageOptions" v-model="filter.lineage" style="flex: auto" filter />
            <div class="exclude-switch">
              Exclude?
              <InputSwitch v-model="filter.exclude"  />
            </div>
            <Button type="button" severity="danger" raised size="small" @click="
              filterGroup.filters?.lineageFilters?.splice(
                filterGroup.filters?.lineageFilters?.indexOf(filter),
                1
              )
              " icon="pi pi-trash" label="">
            </Button>
          </div>
          <div class="flex align-items-center ">
            <small>*This search will return all sublieage of selected lineage.</small >

          </div>
        </div>
      </div>
      
      <div class="button-bar">
        <!-- <SplitButton size="small" icon="pi pi-filter" label="Add AND Filter" :model="filterTypeMethods" @click="addClassicFilter()" /> -->
        <SplitButton size="small" label="" :model="filterTypeMethods" @click="addClassicFilter()" >
          <i class="pi pi-filter"></i> 
          <span style="font-weight: 500;"> &nbsp; Add AND Filter</span>
        </SplitButton>
        <!-- OR part -->
        <Button size="small" icon="pi pi-filter" label="Add OR Group" @click="addOrFilterGroup" :disabled="cantAddOrGroup"/>
      </div>

      <div v-for="subFilterGroup in filterGroup.filterGroups" style="width: 100%">
        <span style="display: block; text-align: center; font-weight: bold; margin-top: 15px;">OR</span>
        <FilterGroup 
        :filterGroup="subFilterGroup" 
        :propertyOptions="propertyOptions" 
        :symbolOptions="symbolOptions"
        :operators="operators" 
        :propertyValueOptions="propertyValueOptions" 
        :repliconAccessionOptions="repliconAccessionOptions"
        :propertiesDict="propertiesDict"
        :lineageOptions="lineageOptions"
        v-on:update-property-value-options="updatePropertyValueOptions" />
        <Button type="button" severity="danger" size="small" style="float: right;" @click="
          filterGroup.filterGroups?.splice(filterGroup.filterGroups?.indexOf(subFilterGroup), 1)
          " @mouseenter="markGroup(subFilterGroup, true)" @mouseleave="markGroup(subFilterGroup, false)">
          <i class="pi pi-trash"></i>
        </Button>
      </div>

    </div>
  </template>


<style scoped>

.single-filter {
  /*  display: flex;*/
  flex-direction: row;
  align-items: center;
  border: 2px solid #e0e0e0;
  border-radius: 20px;
  width: 100%;
  padding: 5px;
  margin: 2.5px;
  justify-content: space-between;
}

.single-filter button {
  margin: 2.5px;
}

.filter-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  border-left: 2px solid var(--grayish);
  border-right: 2px solid var(--grayish);
  border-radius: 2.5%;
  padding: 1em;
  width: 100%;
}

.filter-label {
  margin: 1em;
  /* font-variant: small-caps; */
  text-align: center;
}

.button-bar {
  display: flex;
  flex-direction: row;
  justify-content: space-between;
  /* margin-left: auto; */
  margin: 10px;
}

.button-bar button {
  margin-left: 0.5em;
}

.marked {
  border: 2px solid var(--secondary-color-lighter);
}

.exclude-switch {
  /* font-variant: small-caps; */
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: 0.7em;
  margin: 2.5px;
}

</style>
