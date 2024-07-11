<template>
  <div style="width: 60%;">

    <strong>Sample Details</strong>
    <br>
    <strong> {{ $route.params.id }} </strong>
    <br>

    <SampleDetails :selectedRow="selectedData" :allColumns="allColumns"></SampleDetails>

  </div>
</template>

<script lang="ts">

import API from '@/api/API'

export default {
  name: 'SampleView',
  data() {
    return {
      selectedData: '',
      allColumns: []
    }
  },
  methods: {
    async updateSample() {
      this.selectedData = (await API.getInstance().getSingleSampleGenome(this.$route.params.id)).results[0]
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
