<template>
   <div>Total number of samples in the database: {{ statistics.samples_total}}</div> 
   <div>newest sample: {{ statistics.newest_sample_date}}</div>
</template>
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