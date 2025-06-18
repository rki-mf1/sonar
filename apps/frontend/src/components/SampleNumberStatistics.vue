<template>
  <div class="card-container">
    <PrimeCard class="card">
      <template #content>
        <v-icon name="fa-calendar-alt" fill="var(--text-color)" scale="2" style="float: right" />
        <div style="color: var(--text-color); font-size: 22px; font-weight: bold">
          {{ samplesStore.statistics.latest_sample_date }}
        </div>
        <div style="color: var(--text-color); font-size: 12px; font-weight: 500">
          Date of newest sequence in database
        </div>
      </template>
    </PrimeCard>
    <PrimeCard class="card">
      <template #content>
        <v-icon name="fa-dna" scale="2" fill="var(--text-color)" style="float: right" />
        <div style="color: var(--text-color); font-size: 22px; font-weight: bold">
          {{ filteredCount }} / {{ samplesStore.statistics.samples_total }}
        </div>
        <div style="color: var(--text-color); font-size: 12px; font-weight: 500">
          Sequences selected from database
        </div>
      </template>
    </PrimeCard>
  </div>
</template>

<script lang="ts">
import { useSamplesStore } from '@/stores/samples'

export default {
  name: 'SampleNumberStatistics',
  props: {
    filteredCount: {
      type: Number,
      required: true,
    },
  },
  data() {
    return {
      samplesStore: useSamplesStore(),
    }
  },
  mounted() {},
  methods: {},
}
</script>

<style scoped>
.card {
  background-color: var(--primary-color);
  width: 350px;
  margin: 10px;
  box-shadow: var(--shadow);
  box-sizing: border-box;
}

.card-container {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  align-items: flex-start;
  margin: 5px;
}

:deep(.p-card .p-card-body) {
  padding: 0.8rem !important;
}
</style>
