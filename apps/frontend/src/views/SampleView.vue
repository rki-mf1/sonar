<template>
  <div style="width: 90%">
    <div v-if="selectedData">
      <strong>Sample Details</strong>
      <br />
      <Dialog
        v-model:visible="loading"
        modal
        :closable="false"
        header="Loading..."
        :style="{ width: '10vw', textAlign: 'center' }"
      >
        <div class="flex align-items-center">
          <ProgressSpinner v-if="loading" size="small" style="color: whitesmoke" />
        </div>
      </Dialog>

      <SampleDetails :selected-row="selectedData" :all-columns="allColumns"></SampleDetails>
    </div>

    <strong v-else>ID does not exist</strong>
  </div>
</template>

<script lang="ts">
import API from '@/api/API'

export default {
  name: 'SampleView',
  data() {
    return {
      selectedData: '',
      allColumns: [],
      loading: true
    }
  },
  mounted() {
    this.updateSample()
    this.updatePropertyOptions()
  },
  methods: {
    async updateSample() {
      this.loading = true
      const sampleID = Array.isArray(this.$route.params.id)
        ? this.$route.params.id[0]
        : this.$route.params.id
      this.selectedData = (await API.getInstance().getSingleSampleGenome(sampleID)).results[0]
      this.loading = false
    },
    async updatePropertyOptions() {
      const res = await API.getInstance().getSampleGenomePropertyOptions()
      this.allColumns = res.property_names.concat(['genomic_profiles', 'proteomic_profiles']).sort()
    }
  }
}
</script>

<style scoped></style>
