<template>
  <div v-if="selectedRow">
    <p v-for="(value, key) in selectedRow" :key="key">
      <template v-if="key === 'name'"> <strong>ID:</strong> {{ value }} </template>

      <template v-else-if="key === 'properties' && Array.isArray(value)">
        <strong>{{ key }}:</strong>
        <div v-for="(item, index) in value" :key="index">
          <!-- Verwenden Sie index als Schlüssel -->
          <div v-if="isProperty(item) && item.name === 'lineage'">
            <strong>&nbsp;&nbsp;&nbsp;{{ item.name }}:</strong>
            {{ item.value }}
            (<a
              :href="'https://outbreak.info/situation-reports?pango=' + item.value"
              target="_blank"
              >outbreak.info</a
            >)
          </div>
          <div v-else-if="isProperty(item)">
            <strong>&nbsp;&nbsp;&nbsp;{{ item.name }}:</strong> {{ item.value }}
          </div>
        </div>
      </template>

      <template v-if="key === 'genomic_profiles'">
        <strong>{{ key }}: </strong>
        <div style="white-space: normal; word-wrap: break-word">
          <GenomicProfileLabel
            v-for="(variant, index) in Object.keys(value as GenomicProfile)"
            :key="variant"
            :variant-string="variant"
            :annotations="genomicProfileValue(value)[variant]"
            :is-last="index === Object.keys(value).length - 1"
          />
        </div>
      </template>

      <template v-else-if="key === 'proteomic_profiles'">
        <strong>{{ key }}: </strong>
        <div style="white-space: normal; word-wrap: break-word">
          <GenomicProfileLabel
            v-for="(variant, index) in value"
            :key="variant"
            :variant-string="variant"
            :is-last="index === Object.keys(value).length - 1"
          />
        </div>
      </template>
    </p>
  </div>
</template>

<script lang="ts">
import type { PropType } from 'vue'
import type { GenomicProfile, Property, SampleDetails } from '@/util/types'

export default {
  name: 'SampleDetails',
  props: {
    selectedRow: {
      type: Object as () => SampleDetails,
      required: true,
    },
    allColumns: {
      type: Array as PropType<string[]>,
      required: true,
    },
  },
  methods: {
    isProperty(item: unknown): item is Property {
      return typeof item === 'object' && item != null && 'name' in item && 'value' in item
    },
    genomicProfileValue(value: string | string[] | GenomicProfile | Property[]): GenomicProfile {
      return value as GenomicProfile
    },
  },
}
</script>

<style scoped></style>
