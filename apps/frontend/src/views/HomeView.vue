<template>
  <div class="landing-container">
    <span class="sonar-title">SONAR</span>
    <div class="sonar-icon-wrapper">
      <v-icon name="gi-radar-sweep" scale="5" fill="white" animation="spin" />
    </div>

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
            <h4 class="text-primary mt-0 mb-0">Reference Accession</h4>
            <PrimeDropdown
              v-model="selectedReferenceAccession"
              :options="reference_accessions"
              placeholder="Select a Reference Accession"
              filter
            />
            <h4 class="text-primary mt-0 mb-0">Datasets</h4>
            <MultiSelect
              v-model="selectedDatasets"
              :options="data_sets"
              placeholder="Select Datasets"
              display="chip"
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
import { buildSelectionQuery } from '@/util/routeParams'
import { useSamplesStore } from '@/stores/samples'
import { useRouter } from 'vue-router'

export default {
  name: 'HomeView',
  data() {
    return {
      samplesStore: useSamplesStore(),
      router: useRouter(),
      datasetOptions: {} as Record<
        string,
        { accessions: (string | null)[]; data_sets: (string | null)[] }
      >,
      organisms: [] as string[],
      selectedOrganism: '',
      selectedReferenceAccession: '' as string | null,
      selectedDatasets: [] as (string | null)[],
      loading: false,
    }
  },
  computed: {
    // dynamically based on selectedOrganism
    reference_accessions() {
      return this.datasetOptions[this.selectedOrganism]?.accessions || []
    },
    data_sets() {
      return this.datasetOptions[this.selectedOrganism]?.data_sets || []
    },
  },
  watch: {
    // when ever selectedOrganism is changed, choose first available option
    selectedOrganism() {
      this.selectedReferenceAccession = this.reference_accessions[0] || null
      this.selectedDatasets = this.data_sets
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
      if (this.selectedOrganism && this.selectedReferenceAccession) {
        this.loading = true
        setTimeout(() => {
          const datasets = [...(this.selectedDatasets ?? [])]
          this.samplesStore.setDataset(
            this.selectedOrganism,
            this.selectedReferenceAccession,
            datasets,
          )

          this.router.push({
            name: 'Table',
            query: buildSelectionQuery(this.selectedReferenceAccession, datasets),
          })
          this.loading = false
        }, 50) // delay to trigger loading animation -> there has to be a better solution!
      } else {
        alert('Please select at least an organism and an reference accession.')
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
  min-height: 100vh; /* min-height instead of height so the page scrolls when content overflows */
  width: 100%;
  padding: 2rem 1rem;
  box-sizing: border-box;
  overflow-y: auto;
  background-color: var(--primary-color);
}

.content-container {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 1rem;
  width: clamp(280px, 40vw, 500px); /* responsive: min 280px, scales with viewport, max 500px */
}

/* Responsive adjustments for smaller screens */
@media (max-width: 768px) {
  .landing-container {
    padding: 1rem 0.5rem;
  }
  .content-container {
    width: clamp(260px, 85vw, 500px);
  }
  .sonar-title {
    font-size: 48px;
  }
  .sonar-icon-wrapper {
    transform: scale(0.6);
    margin-bottom: 1.5rem;
  }
}

.sonar-title {
  color: white;
  font-weight: bold;
  font-size: 100px;
}

.sonar-icon-wrapper {
  margin-bottom: 50px;
}
</style>
