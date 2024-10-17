<template>
  <div class="content">
    <div style="height: 95%; width: 95%; display: flex; justify-content: center">
        <Chart type="bar" :data="chartData()" :options="chartOptions()" style="width: 100%" />
    </div>
  </div>
</template>

<script lang="ts">
import { useSamplesStore } from '@/stores/samples';

export default {
  name: 'PlotsView',
  data() {
    return {
      samplesStore: useSamplesStore(),
    }
  },
  methods: {
    chartData() {
      const samples_per_week = this.samplesStore.filteredStatistics ? this.samplesStore.filteredStatistics['samples_per_week']: {}
      const labels = []
      const data = []

      if (samples_per_week && Object.keys(samples_per_week).length > 0) {
        Object.keys(samples_per_week).forEach((key) => {
          labels.push(key)
          data.push(samples_per_week[key])
        })
      } else {
        // Return an empty chart structure
        return {
          labels: ['No data available'], // A label to indicate no data
          datasets: [
            {
              label: 'Samples',
              data: [], // No data points
              backgroundColor: 'rgba(249, 115, 22, 0.2)',
              borderColor: 'rgb(249, 115, 22)',
              borderWidth: 1
            }
          ]
        }
      }

      return {
        labels: labels,
        datasets: [
          {
            label: 'Samples',
            data: data,
            backgroundColor: 'rgba(249, 115, 22, 0.2)',
            borderColor: 'rgb(249, 115, 22)',
            borderWidth: 1
          }
        ]
      }
    },
    chartOptions() {
      const documentStyle = getComputedStyle(document.documentElement)
      const textColor = documentStyle.getPropertyValue('--text-color')
      const textColorSecondary = documentStyle.getPropertyValue('--text-color-secondary')
      const surfaceBorder = documentStyle.getPropertyValue('--surface-border')
      return {
        plugins: {
          legend: {
            display: false
          }
        },
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            ticks: {
              color: textColorSecondary
            },
            grid: {
              color: surfaceBorder
            }
          },
          y: {
            beginAtZero: true,
            ticks: {
              color: textColorSecondary
            },
            grid: {
              color: surfaceBorder
            }
          }
        }
      }
    }
  }
}

</script>

<style scoped>

.content {
  height: 80%;
  width: 98%;
  display: flex;
  flex-direction: row;
  justify-content: space-evenly;
  align-items: center;
  background-color: var(--text-color);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: var(--shadow);
}

</style>
