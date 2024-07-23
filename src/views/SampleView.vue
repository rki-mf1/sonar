<template>
  <div style="width: 90%;">

    <div v-if="selectedData" >
      <strong>Sample Details</strong>
      <br>
      <Dialog v-model:visible="loading" modal :closable="false" header="Loading..." :style="{ width: '10vw' }">
        <ProgressSpinner size="small" v-if="loading" style="color: whitesmoke" />
      </Dialog>
      <SampleDetails :selectedRow="selectedData" :allColumns="allColumns"></SampleDetails>
    </div>
    
    <strong v-else >ID does not exist</strong>

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
  methods: {
    async updateSample() {
      this.loading = true
      this.selectedData = (await API.getInstance().getSingleSampleGenome(this.$route.params.id)).results[0]
      this.loading = false
    },
    async updatePropertyOptions() {
      const res = await API.getInstance().getSampleGenomePropertyOptions();
      this.allColumns = res.property_names.concat(['genomic_profiles', 'proteomic_profiles']).sort();
    },
  },
  mounted() {
    this.updateSample();
    this.updatePropertyOptions()
  }
}

</script>

<style scoped></style>
