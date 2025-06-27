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
            <h4 class="text-primary mt-0 mb-0">Organism</h4>
            <PrimeDropdown
              v-model="selectedOrganism"
              :options="organisms"
              placeholder="Select a Organism"
              filter
            />
            <h4 class="text-primary mt-0 mb-0">Accession</h4>
            <PrimeDropdown
              v-model="selectedAccession"
              :options="accessions"
              placeholder="Select an Accession"
              filter
            />
            <h4 class="text-primary mt-0 mb-0">Dataset</h4>
            <PrimeDropdown
              v-model="selectedDataset"
              :options="data_sets"
              placeholder="Select a Dataset"
              filter
            />
            <PrimeButton
              style="margin-top: 2em"
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
      organisms: [] as string[],
      selectedOrganism: '',
      selectedAccession: '',
      selectedDataset: '',
      loading: false,
    }
  },
  computed: {
    // dynamically based on selectedOrganism
    accessions() {
      return this.datasetOptions[this.selectedOrganism]?.accessions || []
    },
    data_sets() {
      return this.datasetOptions[this.selectedOrganism]?.data_sets || []
    },
  },
  watch: {
    // when ever selectedOrganism is changed, choose first available option
    selectedOrganism() {
      this.selectedAccession = this.accessions[0] || null
      this.selectedDataset = this.data_sets[0] || null
    },
  },
  mounted() {
    this.updateDatasetOptions()
  },
  methods: {
    async updateDatasetOptions() {
      this.datasetOptions = await API.getInstance().getDatasetOptions()
      this.organisms = Object.keys(this.datasetOptions)
      this.selectedOrganism = this.organisms[0]
    },
    proceed() {
      if (this.selectedOrganism && this.selectedAccession) {
        this.loading = true
        setTimeout(() => {
          this.samplesStore.setDataset(
            this.selectedOrganism,
            this.selectedAccession,
            this.selectedDataset,
          )
          this.router.push({ name: 'Home' })
          this.loading = false
        }, 50) // delay to trigger loading animation -> there has to be a better solution!
      } else {
        alert('Please select at least an organism and an accession.')
      }
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
  gap: 1rem;
  width: 30vw;
  height: 35vh;
}
</style>
