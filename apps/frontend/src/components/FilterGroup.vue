<template>
  <div :class="filterGroup.marked ? 'filter-group marked' : 'filter-group'">
    <!-- Lineage Filters -->
    <div v-if= "filterGroup.filters.lineageFilter.isVisible 
    || filterGroup.filters.lineageFilter.lineageList.length>0" class="single-filter">
      <div class="filter-container">
          <span class="filter-label">Lineage</span>
          <MultiSelect 
            v-model="filterGroup.filters.lineageFilter.lineageList" 
            display="chip" 
            :options="lineageOptions" 
            filter
            placeholder="Select Lineages" 
            :virtualScrollerOptions="{ itemSize: 30 }"
            style="flex-grow: 1;  margin-right: 10px;"
          />
          <div class="switch">
            Include Sublineages?
            <InputSwitch v-model="filterGroup.filters.lineageFilter.includeSublineages" />
          </div>
          <div class="switch">
            Exclude?
            <InputSwitch v-model="filterGroup.filters.lineageFilter.exclude" />
          </div>
          <Button 
            type="button" 
            severity="danger" 
            raised size="small" 
            @click="removeLineageFilter(filterGroup, isSubGroup)" 
            icon="pi pi-trash" />
        </div>
    </div>
    <!-- Profile Filters -->
    <div v-for="profileFilter in filterGroup.filters?.profileFilters" class="single-filter">
      <div class="filter-container">
        <span style="font-weight: 500">DNA/AA Profile</span>
          <InputText
            v-model="profileFilter.value" 
            style="flex: auto" 
            :placeholder="'S:L452R, S:del:143-144, del:21114-21929, T23018G'"
            class="mr-1" 
            />
            <div class="switch">
              Exclude?
              <InputSwitch v-model="profileFilter.exclude" />
            </div>
        <!-- the button has to stay outside-->
          <Button 
            type="button" 
            severity="danger" 
            size="small" 
            @click="removeProfileFilter(filterGroup, filterGroup.filters?.profileFilters?.indexOf(profileFilter), isSubGroup)"
            icon="pi pi-trash" 
            class="ml-2 p-button-sm" 
          />
        </div>
    </div>
    <!-- Property Filters -->
    <div v-for="(filter, index) in filterGroup.filters?.propertyFilters" :key="index"class="single-filter">
      <div class="flex align-items-center gap-0">
        <span class="filter-label">Property</span>
        <Dropdown class="flex mr-2" :options="propertyMenuOptions" v-model="filter.propertyName"
          style="flex: 1; min-width: 150px;" @change="updatePropertyValueOptions(filter)" />

        <div v-if="['name', 'length', 'lab'].includes(filter.propertyName) 
                  && (typeof filter.value === 'string' || filter.value === null)"  
            class="mr-2">
          <span class="filter-label">Operator</span>
          <Dropdown :options="localOperators" v-model="filter.filterType" style="flex: 1; min-width: 150px;" />
          <span class="filter-label">Value</span>
          <InputText 
            v-model="filter.value" 
            style="flex: auto" 
          />
        </div>

        <div v-if="isDateArray(filter.value)">
          <div class="filter-container">
            <Calendar 
              v-model="filter.value[0]"  
              style="flex: auto; min-width: 10rem;" 
              showIcon
              dateFormat="yy-mm-dd" 
              ></Calendar>
            <Calendar 
              v-model="filter.value[1]" 
              style="flex: auto;min-width: 10rem;" 
              showIcon
              dateFormat="yy-mm-dd" 
            ></Calendar>
          </div>
        </div>
        <div v-else-if="fetchOptionsProperties.includes(filter.propertyName)">
          <Dropdown 
            :options="propertyValueOptions[filter.propertyName]?.options"
            :loading="propertyValueOptions[filter.propertyName]?.loading" 
            :virtualScrollerOptions="{ itemSize: 30 }"
            v-model="filter.value" 
            style="flex: auto"
            filter 
          />
        </div>
        <Button 
          type="button" raised size="small" 
          @click="removePropertyFilter(filterGroup.filters.propertyFilters, index, isSubGroup)"
          icon="pi pi-trash" 
          label="" 
          severity="danger" />
      </div>
    </div>

    <!-- Replicon Filters -->
    <div v-for="filter in filterGroup.filters?.repliconFilters" class="single-filter">
      <div class="flex flex-column">
        <div class="flex align-items-center">
          <label class="filter-label">Replicon</label>
          <Dropdown :options="repliconAccessionOptions" v-model="filter.accession" style="flex: auto" />
          <div class="switch">
            Exclude?
            <InputSwitch v-model="filter.exclude" />
          </div>
          <Button type="button" size="small" @click="
            filterGroup.filters?.repliconFilters?.splice(
              filterGroup.filters?.repliconFilters?.indexOf(filter),
              1
            )
            " icon="pi pi-trash" />
        </div>
      </div>
    </div>

    <!-- Button Bar -->
    <div class="button-bar">
      <SplitButton size="small" label="" :model="filterTypeMethods">
        <div class="filter-circle">
          <i class="pi pi-filter"></i>
        </div>
        <span style="font-weight: 500;">
          &nbsp; Add AND Filter
        </span>
      </SplitButton>
      <!-- OR part -->
      <Button size="small" icon="pi pi-filter-fill" label="Add OR Group" @click="addOrFilterGroup"
        :disabled="cantAddOrGroup" />
    </div>

    <!-- Sub-Filter Groups -->
    <div v-for="subFilterGroup in filterGroup.filterGroups" style="width: 100%">
      <span style="display: block; text-align: center; font-weight: bold; margin-top: 15px;">OR</span>
      <FilterGroup 
        :filterGroup="subFilterGroup"
        :isSubGroup="true" 
        :propertyMenuOptions="propertyMenuOptions" 
        :symbolOptions="symbolOptions"
        :operators="operators" 
        :propertyValueOptions="propertyValueOptions"
        :repliconAccessionOptions="repliconAccessionOptions" 
        :propertiesDict="propertiesDict"
        :lineageOptions="lineageOptions" 
        v-on:update-property-value-options="updatePropertyValueOptions" />
      <Button type="button" severity="danger" size="small" style="float: right;" 
        @click="filterGroup.filterGroups?.splice(filterGroup.filterGroups?.indexOf(subFilterGroup), 1)" 
        @mouseenter="markGroup(subFilterGroup, true)" 
        @mouseleave="markGroup(subFilterGroup, false)">
        <i class="pi pi-trash"></i>
      </Button>
    </div>
  </div>
</template>

<script lang="ts">

import API from '@/api/API';
import {
  type FilterGroup,
  type PropertyFilter,
  type ProfileFilter,
  type RepliconFilter,
  type LineageFilter,
  DjangoFilterType,
  StringDjangoFilterType,
  DateDjangoFilterType,
  IntegerDjangoFilterType,
} from '@/util/types'

import type { MenuItem } from 'primevue/menuitem'

export default {
  name: 'FilterGroup',
  props: {
    filterGroup: {
      type: Object as () => FilterGroup,
      required: true
    },
    propertyMenuOptions: {
      type: Array as () => string[],
      required: true
    },    
    isSubGroup: {
      type: Boolean,
      default: false,
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
    propertiesDict: {
      type: Object as () => { [key: string]: string },
      required: true
    },
  },
  data() {
    return {
      localOperators: [...this.operators],
      fetchOptionsProperties: ['genome_completeness',
        'sequencing_tech',
        'sequencing_reason',
        'zip_code',
        'country',
        'host',
        'isolation_source'],
      ProfileFilter: {
        label: 'DNA/AA Profile',
        value: '',
        exclude: false,
      } as ProfileFilter,
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
        label: 'Lineages',
        lineageList: [],
        exclude: false,
        includeSublineages: true,
        isVisible: false
      } as LineageFilter,
      // to store the earliest and latest dates for each property.
      dateRanges: {} as { [key: string]: { earliest: string; latest: string } },
    }
  },
  computed: {
    filterTypeMethods(): MenuItem[] {
      const menuItems = []
      menuItems.push({
        label: 'DNA/AA Profile',
        icon: 'pi pi-plus',
        command: () => {
          this.filterGroup.filters.profileFilters.push({ ...this.ProfileFilter })
        }
      })
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
      // only one lineage filter per group
      if (!this.filterGroup.filters.lineageFilter.isVisible) {
        this.LineageFilter.isVisible = true
        menuItems.push({
          label: 'LineageFilter',
          icon: 'pi pi-plus',
          command: () => {
            this.filterGroup.filters.lineageFilter = { ...this.LineageFilter }
          }
        })
      }
      return menuItems
    },
    cantAddOrGroup(): boolean {
      return (
        // no filters
        (this.filterGroup.filters.propertyFilters.length +
        this.filterGroup.filters.profileFilters.length +
        this.filterGroup.filters.repliconFilters.length +
        this.filterGroup.filters.lineageFilter.lineageList.length ==
        0) 
        ||
        // empty standard filters
        (
          (
            (this.filterGroup.filters.profileFilters.length ==1 &&
            this.filterGroup.filters.profileFilters[0].value == "" )
            ||(this.filterGroup.filters.profileFilters.length ==0)
          )
          &&
          (
            (this.filterGroup.filters.propertyFilters.length == 1 &&
            Array.isArray(this.filterGroup.filters.propertyFilters[0].value) &&
            this.filterGroup.filters.propertyFilters[0].value.length==0)
            ||(this.filterGroup.filters.propertyFilters.length ==0)
          ) 
          &&
          (this.filterGroup.filters.lineageFilter.lineageList.length == 0) &&
          (this.filterGroup.filters.repliconFilters.length==0)
      )
    )
    },

    
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
      return this.dateRanges[propertyName];
    },
    addOrFilterGroup() {
      this.filterGroup.filterGroups.push({
        filterGroups: [],
        filters: {
          propertyFilters: [],
          profileFilters: [],
          repliconFilters: [],
          lineageFilter: {
            label: "Lineages",
            lineageList: [],
            exclude: false,
            includeSublineages: true,
            isVisible: false,
          }
        }
      })
    },
    markGroup(group: FilterGroup, mark: boolean) {
      group.marked = mark
    },
    addProfileFilter() {
      this.filterGroup.filters.profileFilters.push({ ...this.ProfileFilter })
    },
    async updatePropertyValueOptions(filter: PropertyFilter) {

      if (this.fetchOptionsProperties.includes(filter.propertyName)) {
        this.$emit('update-property-value-options', filter)
      }
      this.initializeOperators(filter);
      // If the property is a date, set the default value to the date range
      if (filter.propertyName?.includes('date')) {
        const dateRange = await this.get_defaults_earliest_latest_collect_date(filter.propertyName);
        if (dateRange) {
          filter.value = [new Date(dateRange.earliest), new Date(dateRange.latest)];
        }
      } else {
        // default 
        filter.value = ""
      }
    },

    removeProfileFilter(filterGroup: FilterGroup, index: number, isSubGroup:boolean) {
      if (!isSubGroup){
        if (filterGroup.filters?.profileFilters?.length <= 1) {
          filterGroup.filters.profileFilters[0] = {
            label: 'DNA/AA Profile',
            value: '',
            exclude: false,
          };
      }
        else {
          filterGroup.filters.profileFilters.splice(index, 1);
        }
      }      else {
        filterGroup.filters.profileFilters.splice(index, 1);
                                          }
      },

    removeLineageFilter(filterGroup: FilterGroup, isSubGroup:boolean) {
      if (!isSubGroup){
        filterGroup.filters.lineageFilter = {
                                              label: 'Lineages',
                                              lineageList: [],
                                              exclude: false,
                                              includeSublineages: true,
                                              isVisible: true,
                                            };
                      }
                                          
      else {
        filterGroup.filters.lineageFilter = {
                                              label: 'Lineages',
                                              lineageList: [],
                                              exclude: false,
                                              includeSublineages: true,
                                              isVisible: false,
                                            };
                                          }
      },

    removePropertyFilter(propertyFilters:PropertyFilter[], index: number, isSubGroup:boolean){
      if (!isSubGroup){
      if (index == 0) {
        propertyFilters[0] = {
          fetchOptions: false,
          label: 'Property',
          propertyName: 'collection_date',
          filterType: DateDjangoFilterType.RANGE,
          value: [] as (Date)[]};
        }
      else {
        propertyFilters.splice(index, 1);
      }
    }
    else{
      propertyFilters.splice(index, 1)
    }
  },

    initializeOperators(filter: PropertyFilter) {
      const propertyType = this.propertiesDict[filter.propertyName];
      let newOperators = [];
      if (propertyType === 'value_varchar') {
        newOperators = Object.values(StringDjangoFilterType);
      }
      else if (propertyType === 'value_integer') {
        newOperators = Object.values(IntegerDjangoFilterType);
      }
      else if (propertyType === 'value_date') {
        newOperators = Object.values(DateDjangoFilterType);
      } else {
        newOperators = Object.values(DjangoFilterType);
      }
      this.localOperators = newOperators;
      filter.filterType = newOperators[0]
    },
    isDateArray(value: any): value is Date[] {
      return Array.isArray(value) && value.every(item => item instanceof Date);
    },
    isStringOrNull(value: any): boolean {
      return typeof value === 'string' || typeof value === null ;
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

.exclude-switch {
  /* font-variant: small-caps; */
  display: flex;
  flex-direction: column;
  align-items: center;
  font-size: 0.7em;
  margin: 2.5px;
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

.switch {
  /* font-variant: small-caps; */
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  font-size: 0.7em;
  margin: 2.5px;
}

</style>
