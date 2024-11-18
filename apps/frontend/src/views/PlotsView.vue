<template>
  <div class="container">
    <!-- seq per week plot-->
    <div class="row">
      <div class="col-lineage">
        <!-- Show Skeleton while loading, and Panel with Bar Chart after loading -->
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="100%" height="250px" />
        <Panel v-else header="Week Calendar" class="w-full shadow-2">
          <div style="height: 95%; width: 95%; display: flex; justify-content: center">
            <Chart ref="weekCalendarPlot" type="bar" :data="chartData()" :options="chartOptions()"
              style="width: 100%" />
          </div>
        </Panel>
      </div>
    </div>
<!-- lineage plots-->
    <div class="row">
      <div class="col-lineage">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="100%" height="250px" />
        <Panel v-else header="Lineage Plot" class="w-full shadow-2">
          <!-- lineage area plot-->
          <h4>Area Plot - COVID-19 Lineages Over Time</h4>
          <div class="h-30rem plot">

            <Chart type="line" ref="lineageAreaPlot" :data="lineage_areaData()" :options="lineage_areaChartOptions()"
              style="width: 100%; height: 100%" />
          </div>
          <!-- lineage bar plot-->
          <h4>Stacked Bar Plot - Lineage Distribution by Calendar Week</h4>
          <div class="h-26rem plot">
            <Chart type="bar" ref="lineageBarPlot" :data="lineage_barData()" :options="lineage_barChartOptions()"
              style="width: 100%; height: 100%" />
          </div>
        </Panel>
      </div>
    </div>

    <div class="row">
      <div v-if="samplesStore.propertyOptions.includes('sequencing_tech')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Sequencing Tech." class="w-full shadow-2">
          <div style="justify-content: center" class="h-20rem">
            <Chart type="polarArea" :data="sequencingTechChartData()" :options="sequencingTechChartOptions()" style=""
              class="h-full" />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyOptions.includes('genome_completeness')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Genome completeness" class="w-full shadow-2">
          <div style=" display: flex; justify-content: center" class="h-20rem plot">
            <Chart type="pie" :data="genomeCompleteChart()" :options="genome_pieChartOptions()" style="" />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyOptions.includes('sequencing_reason')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Sequencing Reason" class="w-full shadow-2">
          <div class="h-20rem plot">
            <Chart type="doughnut" :data="sequencingReasonChartData()" :options="sequencingReasonChartOptions()" />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyOptions.includes('zip_code')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Zip Code" class="w-full shadow-2">
          <div class="h-20rem plot">
            <Chart type="bar" :data="zipCodeChartData()" :options="zipCodeChartOptions()" class="w-full h-full" />
          </div>
        </Panel>
      </div>


      <div v-if="samplesStore.propertyOptions.includes('sample_type')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Sample Type" class="w-full shadow-2">
          <div class="h-20rem plot">
            <Chart type="pie" :data="sampleTypeChartData()" :options="sampleTypeChartOptions()" />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyOptions.includes('lab')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Lab" class="w-full shadow-2">
          <div class="h-20rem plot">
            <Chart type="bar" :data="labChartData()" :options="labChartOptions()" class="w-full h-full" />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyOptions.includes('host')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Host" class="w-full shadow-2">
          <div class="h-20rem plot">
            <Chart type="bar" :data="hostChartData()" :options="hostChartOptions()" class="w-full h-full" />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyOptions.includes('length')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Length" class="w-full shadow-2 ">
          <div class="h-20rem plot">
            <Chart type="bar" :data="lengthChartData()" :options="lengthChartOptions()"
              style="width: 100%; height: 100%" /> <!-- scatter -->
          </div>
        </Panel>
      </div>
          </div>
  </div>
</template>

<script lang="ts">
import { useSamplesStore } from '@/stores/samples';
import type { LineageBarChartData } from '@/util/types';
import { RiAndroidFill } from 'oh-vue-icons/icons';

export default {
  name: 'PlotsView',
  data() {
    return {
      samplesStore: useSamplesStore(),
      chartInstances: {}
    }
  },
  watch: {
    // "samplesStore.filteredStatistics"(newValue) {
    //   this.updateCharts(); // Update charts when data changes
    // }
  },
  mounted() {
  },
  beforeUnmount() {
  },
  methods: {
    genomeCompleteChart() {
      const documentStyle = getComputedStyle(document.body);
      const _data = this.samplesStore.filteredStatistics ? this.samplesStore.filteredStatistics['genomecomplete_chart'] : {}
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData();
      }
      return {
        labels: Object.keys(_data),
        datasets: [
          {
            data: Object.values(_data),
            backgroundColor: [documentStyle.getPropertyValue('--cyan-500'), documentStyle.getPropertyValue('--orange-500'), documentStyle.getPropertyValue('--gray-500')],
            hoverBackgroundColor: [documentStyle.getPropertyValue('--cyan-400'), documentStyle.getPropertyValue('--orange-400'), documentStyle.getPropertyValue('--gray-400')]
          }
        ]
      };
    },
    genome_pieChartOptions() {
      const documentStyle = getComputedStyle(document.documentElement);
      const textColor = '#333';

      return {
        animation: false,
        plugins: {
          legend: {
            labels: {
              usePointStyle: true,
              color: textColor
            }
          }
        },
        responsive: true,
        maintainAspectRatio: false,
      };
    },
    lineage_barData() {
      // Access lineage_bar_chart data from filteredStatistics
      const _data: LineageBarChartData[] = this.samplesStore.filteredStatistics
        ? this.samplesStore.filteredStatistics['lineage_bar_chart']
        : [];
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData();
      }
      let datasets = [];
      let weeks = [];

      const lineages = [...new Set(_data.map(item => item.lineage))];
      weeks = [...new Set(_data.map(item => item.week))];

      datasets = lineages.map(lineage => ({
        label: lineage,
        data: weeks.map(
          week =>
            _data.find(item => item.week === week && item.lineage === lineage)?.percentage || 0
        ),
        backgroundColor: this.getColor(lineage),
      }));


      return { labels: weeks, datasets };
    },
    lineage_barChartOptions() {
      return {
        animation: false,
        plugins: {
          legend: { display: true, position: "bottom", },
          // tooltip: {
          //   mode: 'index',
          //   intersect: false,
          // },
          zoom: {
            zoom: {
              wheel: { enabled: true },
              pinch: { enabled: true },
              mode: 'x',
            },
            pan: {
              enabled: true,
              mode: 'x'
            },
          }
        },
        scales: {
          x: {
            stacked: true,
            beginAtZero: true,
            min: 0,
            max: 30,
          },
          y: {
            stacked: true,
            beginAtZero: true,
            max: 100,
            ticks: {
              callback: function (value: number) {
                return value + '%';
              },
            },
          },
        },
        responsive: true,
        maintainAspectRatio: false,
      }
    },
    lineage_areaData() {
      // Extract the data, ensuring it's an array
      const _data = this.samplesStore.filteredStatistics
        ? this.samplesStore.filteredStatistics['lineage_area_chart'] : [];
      if (!_data || Object.keys(_data).length === 0) {
        return this.emptyChartData();
      }
      let datasets = [];
      let dates = [];
      // Extract unique lineages and dates
      const lineages = [...new Set(_data.map(item => item.lineage))];
      dates = [...new Set(_data.map(item => item.date))];

      dates.sort();
      datasets = lineages.map(lineage => ({
        label: lineage,
        data: dates.map(date =>
          _data.find(item => item.date === date && item.lineage === lineage)
            ?.percentage || 0
        ),
        fill: true,
        backgroundColor: this.getColor(lineage),
      }));


      // Return the data structure expected by the area chart component
      return { labels: dates, datasets };
    },
    lineage_areaChartOptions() {
      return {
        animation: false,
        plugins: {
          legend: {
            display: false, position: "bottom",
          },
          zoom: {
            zoom: {
              wheel: { enabled: true },
              pinch: { enabled: true },
              mode: 'x',
            },
            pan: {
              enabled: true,
              mode: 'x'
            },
          },
          decimation: {
            enabled: true,
            algorithm: 'lttb',
            samples: 1000,
            threshold: 5
          }
        },
        scales: {
          x: {
            stacked: true,
            beginAtZero: true,
            min: 0,
            max: 10,
          },
          y: {
            stacked: true,
            beginAtZero: true,
            max: 100,
            ticks: {
              callback: function (value: number) {
                return value + '%'; // Add percentage symbol
              },
            },
          },
        },
        responsive: true,
        maintainAspectRatio: false,
      }
    },
    chartData() {
      const samples_per_week = this.samplesStore.filteredStatistics ? this.samplesStore.filteredStatistics['samples_per_week'] : {}
      const labels: string[] = []
      const data: number[] = []

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
        animation: false,
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
    },
    sequencingTechChartData() {
      const _data = this.samplesStore.filteredStatistics ? this.samplesStore.filteredStatistics['sequencing_tech'] : {};
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData();
      }
      return {
        labels: Object.keys(_data),
        datasets: [
          {
            data: Object.values(_data),
            backgroundColor: Object.keys(_data).map(x => this.getColor(x)),

          }
        ]
      };
    },
    sequencingTechChartOptions() {
      return {
        animation: false,
        plugins: {
          legend: {
            display: true,
            position: 'right'
          },
          responsive: true,
          maintainAspectRatio: false,
          zoom: {
            pan: {
              enabled: true,
              mode: 'yx',
            },
            zoom: {
              wheel: {
                enabled: true,
                speed: 0.5
              },
              mode: 'xy',
            },
          }
        },
        responsive: true,
        maintainAspectRatio: false,
      };
    },
    sequencingReasonChartData() {
      const _data = this.samplesStore.filteredStatistics ? this.samplesStore.filteredStatistics['sequencing_reason'] : {};
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData();
      }
      return {
        labels: Object.keys(_data),
        datasets: [
          {
            data: Object.values(_data),
            backgroundColor: Object.keys(_data).map(x => this.getColor(x)),
            // hoverBackgroundColor: Object.keys(_data).map(x => this.getHoverColor(x))
          }
        ]
      };
    },
    sequencingReasonChartOptions() {
      return {
        animation: false,
        plugins: {
          legend: {
            display: true,
            position: 'right'
          }
        },
        responsive: true,
        maintainAspectRatio: false,
      };
    },
    lengthChartData() {
      const _data = this.samplesStore.filteredStatistics ? this.samplesStore.filteredStatistics['length'] : {};
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData();
      }
      return {
        labels: Object.keys(_data),
        datasets: [
          {
            data: Object.values(_data),
            backgroundColor: '#FFD1DC'
          }
        ]
      };
    },
    lengthChartOptions() {
      return {
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          y: {
            beginAtZero: true
          }
        },
        responsive: true,
        maintainAspectRatio: false,
      };
    },
    hostChartData() {
      const _data = this.samplesStore.filteredStatistics ? this.samplesStore.filteredStatistics['host'] : {};
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData();
      }
      return {
        labels: Object.keys(_data),
        datasets: [
          {
            label: 'Samples',
            data: Object.values(_data),
            backgroundColor: '#FFA726'
          }
        ]
      };
    },
    hostChartOptions() {
      return {
        animation: false,
        indexAxis: 'y',
        plugins: {
          legend: {
            display: false
          }
        },
        scales: {
          x: {
            beginAtZero: true
          }
        },
        responsive: true,
        maintainAspectRatio: false,
      };
    },
    labChartData() {
      const _data = this.samplesStore.filteredStatistics ? this.samplesStore.filteredStatistics['lab'] : {};
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData();
      }
      return {
        labels: Object.keys(_data),
        datasets: [
          {
            label: 'Samples',
            data: Object.values(_data),
            backgroundColor: '#FFA726'
          }
        ]
      };
    },
    labChartOptions() {
      return {
        plugins: {
          legend: {
            display: false

          },
          zoom: {
            zoom: {
              wheel: { enabled: true },
              pinch: { enabled: true },
              mode: 'x',
            },
            pan: {
              enabled: true,
              mode: 'x'
            },
            limits: {
              x: { min: 0, minRange: 10 },
            },
          },

        },
        scales: {
          x: { stacked: true },
          y: { stacked: true, beginAtZero: true }
        },
        responsive: true,
        maintainAspectRatio: false,
      };
    },
    zipCodeChartData() {
      const _data = this.samplesStore.filteredStatistics ? this.samplesStore.filteredStatistics['zip_code'] : {};
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData();
      }
      return {
        labels: Object.keys(_data),
        datasets: [
          {
            label: 'Samples',
            data: Object.values(_data),
            backgroundColor: '#42A5F5'
          }
        ]
      };
    },
    zipCodeChartOptions() {
      return {
        animation: false,
        indexAxis: 'y', // Makes the bar chart horizontal
        plugins: {
          legend: {
            display: false
          },
          zoom: {
            pan: {
              enabled: true,
              mode: 'yx',
            },
            zoom: {
              wheel: {
                enabled: false,
                speed: 0.5
              },
              mode: 'xy',
            },
            limits: {
              x: { min: 0, minRange: 10 },
            },
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            min: 0,
          }
        },
        responsive: true,
        maintainAspectRatio: false,
      };
    },
    sampleTypeChartData() {
      const _data = this.samplesStore.filteredStatistics ? this.samplesStore.filteredStatistics['sample_type'] : {};
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData();
      }
      return {
        labels: Object.keys(_data),
        datasets: [
          {
            data: Object.values(_data),
            backgroundColor: Object.keys(_data).map(x => this.getColor(x)),

          }
        ]
      };
    },
    sampleTypeChartOptions() {
      return {
        animation: false,
        plugins: {
          legend: {
            display: true,
            position: 'right'
          }
        },
        responsive: true,
        maintainAspectRatio: false,
      };
    },
    getHoverColor(str: string) {
      const hash = this.hashString(str);
      const hue = (hash % 360 + 30) % 360;  // Offset hue for hover for differentiation
      return `hsl(${hue}, 80%, 70%)`; // Adjusted saturation and lightness for hover effect
    },
    getColor(str: string) {
      const hash = this.hashString(str);
      const hue = hash % 360;  // Base hue
      return `hsl(${hue}, 70%, 50%)`;  // Slightly darker for main color
    },
    hashString(str: string | null | undefined) {
      let hash = 0;
      if (!str) {
        return hash; // in case there is no prop (null or undefined)
      }
      for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
      }
      return Math.abs(hash); //* (Math.random() * (10 - 5) + 5);
    },

    emptyChartData(label = 'No data available') {
      return {
        labels: [label], // A label to indicate no data
        datasets: [
          {
            label: 'No data available',
            data: [], // No data points
          }
        ]
      };
    },

    isDataEmpty(data: { [key: string]: any }): boolean {
      return (!data || Object.keys(data).length === 0
        || Object.keys(data).length === 1 && Object.keys(data)[0] == 'null')
    },
  }
}

</script>

<style scoped>
.content {
  height: 80%;
  width: 98%;
  display: flex;
  justify-content: space-evenly;
  align-items: center;
  background-color: var(--text-color);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: var(--shadow);
}

.container {
  display: flex;
  flex-wrap: wrap;
  flex-direction: row;
  overflow-x: auto;
  width: 98%;
}
.col-lineage {
  width: 98%;
}
.row {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  width: 98%;
}

.col {
  flex: 1 1 25%;
  
  max-width: 25%;
  padding: 0.5rem;
  box-sizing: border-box;
}

.plot {
  display: flex; 
  justify-content: center;
  height: 100%; 
  width: 100%; 
}

/* Panel-Styling */
.panel {
  width: 100%;
  height: auto;
  max-width: 100%;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
  padding: 1rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.row:nth-child(1),
.row:nth-child(2) {
  .col {
    flex: 1 1 100%; 
    max-width: 100%;
  }
}

/* Media Queries for different screen sizes */
@media (max-width: 1024px) {
  .row:nth-child(3),
  .row:nth-child(4) {
    .col {
      flex: 1 1 50%; 
      max-width: 50%;
    }
  }

  .row:nth-child(1),
  .row:nth-child(2) {
    .col {
      flex: 1 1 90%; /* Größe reduzieren */
      max-width: 90%;
    }
  }
}

@media (max-width: 768px) {
  .row:nth-child(3),
  .row:nth-child(4) {
    .col {
      flex: 1 1 50%; 
      max-width: 50%;
    }
  }

  .row:nth-child(1),
  .row:nth-child(2) {
    .col {
      flex: 1 1 100%;
      max-width: 100%;
    }
  }
}
</style>
