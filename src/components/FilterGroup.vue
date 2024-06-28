<script lang="ts">

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
  type RepliconFilter
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
    operators: {
      type: Array as () => string[],
      required: true
    },
    propertyValueOptions: {
      type: Object as () => { [key: string]: { options: string[]; loading: boolean } },
      required: true
    }
  },
  data() {
    return {
      fetchOptionsProperties: ['sequencing_tech', 'sequencing_reason', 'zip_code'],
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
      } as { [key: string]: ProfileFilter }
    }
  },
  computed: {
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
      }
      )
      return menuItems
    },
    cantAddOrGroup(): boolean {
      return (
        this.filterGroup.filters.propertyFilters.length +
          this.filterGroup.filters.profileFilters.length +
          this.filterGroup.filters.repliconFilters.length ==
        0
      )
    }
  },
  methods: {
    addOrFilterGroup() {
      this.filterGroup.filterGroups.push({
        filterGroups: [],
        filters: { propertyFilters: [], profileFilters: [], repliconFilters: []}
      })
    },
    markGroup(group: FilterGroup, mark: boolean) {
      group.marked = mark
    },
    addClassicFilter() {
      this.filterGroup.filters.profileFilters.push({ ...this.ClassicFilter })
    },
    updatePropertyValueOptions(filter: PropertyFilter) {
      if (this.fetchOptionsProperties.includes(filter.propertyName)) {
        this.$emit('update-property-value-options', filter.propertyName)
      }
    }
  }
}
</script>


<template>
    <div :class="filterGroup.marked ? 'filter-group marked' : 'filter-group'">
      <div v-for="filter in filterGroup.filters?.propertyFilters" class="single-filter">
        <span class="filter-label">Property</span>
        <Dropdown :options="propertyOptions" v-model="filter.propertyName" style="flex: auto"
          @change="updatePropertyValueOptions(filter)" />
        <Dropdown :options="operators" v-model="filter.filterType" style="flex: auto" />
        <Calendar v-if="filter.propertyName?.includes('date')" v-model="filter.value" style="flex: auto"
          dateFormat="yy-mm-dd" selectionMode="range"/>
        <Dropdown v-else-if="fetchOptionsProperties.includes(filter.propertyName)"
          :options="propertyValueOptions[filter.propertyName]?.options"
          :loading="propertyValueOptions[filter.propertyName]?.loading" v-model="filter.value" style="flex: auto" />
        <InputText v-else v-model="filter.value" style="flex: auto" />
        <Button size="small" @click="
          filterGroup.filters?.propertyFilters?.splice(
            filterGroup.filters?.propertyFilters?.indexOf(filter),
            1
          )
          ">
          <i class="pi pi-trash"></i>
        </Button>
      </div>
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
        <Button size="small" @click="
          filterGroup.filters?.profileFilters?.splice(
            filterGroup.filters?.profileFilters?.indexOf(filter),
            1
          )
          ">
          <i class="pi pi-trash"></i>
        </Button>
      </div>
      <div v-for="filter in filterGroup.filters?.repliconFilters" class="single-filter">
        <span class="filter-label">Replicon</span>
        <Dropdown :options="repliconAccessionOptions" v-model="filter.accession" style="flex: auto" />
        <div class="exclude-switch">
          Exclude?
          <InputSwitch v-model="filter.exclude" />
        </div>
        <Button size="small" @click="
          filterGroup.filters?.repliconFilters?.splice(
            filterGroup.filters?.repliconFilters?.indexOf(filter),
            1
          )
          ">
          <i class="pi pi-trash"></i>
        </Button>
      </div>
      <div class="button-bar">
        <!-- <SplitButton size="small" icon="pi pi-filter" label="Add AND Filter" :model="filterTypeMethods" @click="addClassicFilter()" /> -->
        <SplitButton size="small" label="" :model="filterTypeMethods" @click="addClassicFilter()" >
          <i class="pi pi-filter"></i> 
          <span style="font-weight: 500;"> &nbsp; Add AND Filter</span>
        </SplitButton>
        <Button size="small" icon="pi pi-filter" label="Add OR Group" @click="addOrFilterGroup" :disabled="cantAddOrGroup"/>
      </div>
      <div v-for="subFilterGroup in filterGroup.filterGroups" style="width: 100%">
        <span style="display: block; text-align: center; font-weight: bold; margin-top: 15px;">OR</span>
        <FilterGroup :filterGroup="subFilterGroup" :propertyOptions="propertyOptions" :symbolOptions="symbolOptions"
          :operators="operators" :propertyValueOptions="propertyValueOptions" :repliconAccessionOptions="repliconAccessionOptions"
          v-on:update-property-value-options="updatePropertyValueOptions" />
        <Button size="small" style="float: right;" @click="
          filterGroup.filterGroups?.splice(filterGroup.filterGroups?.indexOf(subFilterGroup), 1)
          " @mouseenter="markGroup(subFilterGroup, true)" @mouseleave="markGroup(subFilterGroup, false)">
          <i class="pi pi-trash"></i>
        </Button>
      </div>
    </div>
  </template>


<style scoped>

.single-filter {
  display: flex;
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
