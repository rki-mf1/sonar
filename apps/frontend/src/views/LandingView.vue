<template>
  <div class="landing-container">
    <span style="color: white; font-weight: bold; font-size: 100px">SONAR</span>
    <v-icon
      name="gi-radar-sweep"
      scale="5"
      fill="white"
      animation="spin"
      style="margin-bottom: 50px"
    />

    <div
      v-animateonscroll="{ enterClass: 'fadein', leaveClass: 'fadeout' }"
      class="shadow-4 align-center animation-duration-1000 animation-ease-in-out mb-4"
    >
      <PrimeCard>
        <template #title>
          <h3 class="text-primary mt-4" style="text-align: center">Data Selection</h3>
        </template>
        <template #content>
          <div class="content-container">
            <PrimeDropdown
              v-model="selectedPathogen"
              :options="pathogens"
              placeholder="Select a Pathogen"
              filter
            />
            <PrimeDropdown
              v-model="selectedDataset"
              :options="datasets"
              placeholder="Select a Dataset"
              filter
            />
            <PrimeButton
              label="Proceed"
              severity="warning"
              raised
              :loading="loading"
              @click="proceed"
            />
          </div>
        </template>
      </PrimeCard>
    </div>
  </div>
</template>

<script lang="ts">
import API from '@/api/API'
import { useSamplesStore } from '@/stores/samples'
import { useRouter } from 'vue-router'

export default {
  name: 'LandingView',
  data() {
    return {
      samplesStore: useSamplesStore(),
      router: useRouter(),
      datasetOptions: {},
      pathogens: [] as string[],
      selectedPathogen: '',
      selectedDataset: '',
      loading: false,
    }
  },
  mounted() {
    this.updateDatasetOptions()
  },
  methods: {
    async updateDatasetOptions() {
      this.datasetOptions = await API.getInstance().getDatasetOptions()
      this.pathogens = Object.keys(this.datasetOptions)
      this.selectedPathogen = this.pathogens[0]
      this.selectedDataset = this.datasets[0] || null
    },
    proceed() {
      if (this.selectedPathogen && this.selectedDataset) {
        this.loading = true
        setTimeout(() => {
          this.samplesStore.setDataset(this.selectedPathogen, this.selectedDataset)
          this.router.push({ name: 'Home' })
          this.loading = false
        }, 50) // delay to trigger loading animation -> there has to be another solution!
      } else {
        alert('Please select both a pathogen and a dataset.')
      }
    },
  },
  computed: {
    // dynamically based on selectedPathogen
    datasets() {
      return this.datasetOptions[this.selectedPathogen] || []
    },
  },
}
</script>

<style scoped>
.landing-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  height: 100vh;
  width: 100%;
  background-color: var(--primary-color);
}

.content-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2rem;
  width: 25vw;
  height: 25vh;
}
</style>
