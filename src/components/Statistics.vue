<script lang="ts">
 import API from '@/api/API';
 export default{
     name: "Statistics",
     data() {
         return {
         statistics: {
             samples_total: 0,
             newest_sample_date: ""
         }
     }
     },
     methods:{
         async fetchStatistics() {
             const sample_statistics = await API.getInstance().getSampleStatistics()
             this.statistics.samples_total=sample_statistics.samples_total
             this.statistics.newest_sample_date=sample_statistics.newest_sample_date
             console.log(sample_statistics)
         }
     },
     mounted(){
         this.fetchStatistics() 
     }
     }
 </script>

<template>
    <Card class="card" style="background-color: var(--secondary-color);">
        <template #content>
        <v-icon name="fa-dna" scale="2.5" fill="var(--text-color)" style="float: right;"/>
        <div style="color: var(--text-color); font-size: 22px; font-weight: bold;">{{ statistics.samples_total }}</div>
        <div style="color: var(--text-color); font-size: 12px; font-weight: 500; margin-top: 10px;">Total number of sequences in database</div>
        </template>
    </Card>
    <Card class="card">
        <template #content>
        <v-icon name="fa-calendar-alt" fill="var(--text-color)" scale="2.5" style="float: right;"/>
        <div style="color: var(--text-color); font-size: 22px; font-weight: bold;">{{ statistics.newest_sample_date }}</div>
        <div style="color: var(--text-color); font-size: 12px; font-weight: 500; margin-top: 10px;">Date of newest sequence</div>
        </template>
    </Card>
</template>

<style scoped>
  .card {
    width: 25%;
    background-color: var(--primary-color);
    margin: 20px;
    box-shadow: var(--shadow);
  }

</style>