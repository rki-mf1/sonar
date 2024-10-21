<template>
    <div class="card-container">
        <Card class="card">
            <template #content >
                <v-icon 
                    name="fa-calendar-alt" 
                    fill="var(--text-color)" 
                    scale="2" 
                    style="float: right;" />
                <div 
                    style="color: var(--text-color); font-size: 22px; font-weight: bold;"
                    >{{ statistics.latest_sample_date }}</div>
                <div 
                    style="color: var(--text-color); font-size: 12px; font-weight: 500;"
                    >Date of newest sequence in database</div>
            </template>
        </Card>
        <Card class="card" style="background-color: var(--secondary-color);">
        <template #content>
            <v-icon 
                name="fa-dna" 
                scale="2" 
                fill="var(--text-color)" 
                style="float: right;" />
            <div 
                style="color: var(--text-color); font-size: 22px; font-weight: bold;"
                >{{ filteredCount }} / {{ statistics.samples_total }}
            </div>
            <div 
                style="color: var(--text-color); font-size: 12px; font-weight: 500;">
                Sequences selected from database
            </div>
        </template>
        </Card>
    </div>

</template>

<script lang="ts">

import API from '@/api/API';
import type { PropType } from 'vue';

export default {
    name: "Statistics",
    props: {
        filteredCount: {
            // type: Object as PropType<number>, 
            required: true,
        }
    },
    data() {
        return {
            statistics: {
                distinct_mutations_count: 0,
                samples_total: 0,
                latest_sample_date: ""
            }
        }
    },
    methods: {
        async fetchStatistics() {
            const sample_statistics = await API.getInstance().getSampleStatistics()
            this.statistics.distinct_mutations_count = sample_statistics.distinct_mutations_count
            this.statistics.samples_total = sample_statistics.samples_total
            this.statistics.latest_sample_date = sample_statistics.latest_sample_date
        }
    },
    mounted() {
        this.fetchStatistics()
    }
}
</script>

<style scoped>
.card {
    background-color: var(--primary-color);
    width: 350px;
    margin: 10px;
    box-shadow: var(--shadow);
    box-sizing: border-box; 
};
.card-container {
    display: flex;
    flex-direction: column;
    justify-content: flex-start; 
    align-items: flex-start; 
    margin: 5px;
}

::v-deep .p-card .p-card-body {
    padding: 0.8rem !important;
}
</style>