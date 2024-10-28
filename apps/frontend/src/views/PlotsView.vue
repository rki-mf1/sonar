<template>
  <div class="">
    <!-- Row 1: Week Calendar (Full-width) -->
    <div class="grid m-1">
      <div class="col-12">
        <!-- Show Skeleton while loading, and Panel with Bar Chart after loading -->
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="100%" height="250px" />
        <Panel v-else header="Week Calendar" class="w-full">
          <div style="height: 95%; width: 95%; display: flex; justify-content: center">
            <Chart ref="weekCalendarPlot" type="bar" :data="chartData()" :options="chartOptions()"
              style="width: 100%" />
          </div>
        </Panel>
      </div>
    </div>

    <div class="grid m-1">
      <div class="col-12">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="100%" height="250px" />
        <Panel v-else header="Lineage Plot" class="w-full">
          <h4>Area Plot - COVID-19 Lineages Over Time</h4>
          <div style="width: 100%; display: flex; justify-content: center" class="h-30rem">
            <Chart type="line" ref="lineageAreaPlot" :data="lineage_areaData()" :options="lineage_areaChartOptions()"
              style="width: 100%; height: 100%" />
          </div>
          <h4>Stacked Bar Plot - Lineage Distribution by Calendar Week</h4>
          <div style="width: 100%; display: flex; justify-content: center" class="h-26rem">
            <Chart type="bar" ref="lineageBarPlot" :data="lineage_barData()" :options="lineage_barChartOptions()"
              style="width: 100%; height: 100%" />
          </div>
        </Panel>
      </div>
    </div>

    <!-- 2x2 Grid Layout -->
    <div class="grid m-1">
      <!-- First Chart (Row 1, Column 1) -->
      <div class="col-12 md:col-6">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Sequencing Tech." class="w-full">
          <div style="display: flex; justify-content: center" class="h-20rem">
            <Chart type="polarArea" :data="sequencingTechChartData()" :options="sequencingTechChartOptions()" style=""
              class="h-full" />
          </div>
        </Panel>
      </div>

      <!-- Second Chart (Row 1, Column 2) -->
      <div class=" col-12 md:col-6">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Genome completeness" class="w-full">
          <div style="height: 95%; width: 95%; display: flex; justify-content: center" class="h-20rem">
            <Chart type="pie" :data="genomeCompleteChart()" :options="genome_pieChartOptions()" style="" />
          </div>
        </Panel>
      </div>

      <!-- Third Chart (Row 2, Column 1) -->
      <div class="col-12 md:col-6">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Sequencing Reason" class="w-full">
          <div style="height: 95%; width: 95%; display: flex; justify-content: center" class="h-20rem">
            <Chart type="doughnut" :data="sequencingReasonChartData()" :options="sequencingReasonChartOptions()" />
          </div>
        </Panel>
      </div>

      <!-- Fourth Chart (Row 2, Column 2) -->
      <div class="col-12 md:col-6">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Zip Code" class="w-full">
          <div style=" display: flex; justify-content: center" class="h-20rem">
            <Chart type="bar" :data="zipCodeChartData()" :options="zipCodeChartOptions()" class="w-full h-full" />
          </div>
        </Panel>
      </div>
    </div>

    <!-- 2x2 Grid Layout -->
    <div class="grid m-1">
      <!-- First Chart (Row 1, Column 1) -->
      <div class="col-12 md:col-6">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Sample Type" class="w-full">
          <div style="height: 95%; width: 95%; display: flex; justify-content: center" class="h-20rem">
            <Chart type="pie" :data="sampleTypeChartData()" :options="sampleTypeChartOptions()" />
          </div>
        </Panel>
      </div>

      <!-- Second Chart (Row 1, Column 2) -->
      <div class="col-12 md:col-6">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Lab" class="w-full">
          <div style="height: 95%; width: 95%; display: flex; justify-content: center" class="h-20rem">
            <Chart type="bar" :data="labChartData()" :options="labChartOptions()" class="w-full h-full" />
          </div>
        </Panel>
      </div>

      <!-- Third Chart (Row 2, Column 1) -->
      <div class="col-12 md:col-6">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Host" class="w-full">
          <div style="display: flex; justify-content: center" class="h-20rem">
            <Chart type="bar" :data="hostChartData()" :options="hostChartOptions()" class="w-full h-full" />
          </div>
        </Panel>
      </div>

      <!-- Fourth Chart (Row 2, Column 2) -->
      <div class="col-12 md:col-6">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Length" class="w-full">
          <div style="width: 100%; display: flex; justify-content: center" class="h-20rem">
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
    //this.initializeCharts();
  },
  beforeUnmount() {
    //this.destroyAllCharts();
  },
  methods: {
    initializeCharts() {
      // Initialize all charts by accessing their refs
      this.$refs.weekCalendarPlot && this.createOrUpdateChart('weekCalendarPlot', this.chartData(), this.chartOptions());
      this.$refs.lineageAreaPlot && this.createOrUpdateChart('lineageAreaPlot', this.lineage_areaData(), this.lineage_areaChartOptions());
      this.$refs.lineageBarPlot && this.createOrUpdateChart('lineageBarPlot', this.lineage_barData(), this.lineage_barChartOptions());
      // Add any additional charts here
    },
    updateCharts() {
      // Update data of each chart when the data changes
      if (this.chartInstances.weekCalendarPlot) {
        this.chartInstances.weekCalendarPlot.data = this.chartData();
        this.chartInstances.weekCalendarPlot.update();
      }
      if (this.chartInstances.lineageAreaPlot) {
        this.chartInstances.lineageAreaPlot.data = this.lineage_areaData();
        this.chartInstances.lineageAreaPlot.update();
      }
      if (this.chartInstances.lineageBarPlot) {
        this.chartInstances.lineageBarPlot.data = this.lineage_barData();
        this.chartInstances.lineageBarPlot.update();
      }
    },
    destroyAllCharts() {
      // Destroy all chart instances on component unmount
      if (this.chartInstances) {
        Object.keys(this.chartInstances).forEach((chartKey) => {
          this.chartInstances[chartKey].destroy();
          delete this.chartInstances[chartKey];
        });
      }

    },
    createOrUpdateChart(refName, data, options) {
      const chartRef = this.$refs[refName];
      if (this.chartInstances[refName]) {
        // If chart instance already exists, destroy it before recreating
        this.chartInstances[refName].destroy();
      }
      // Create and store new chart instance
      this.chartInstances[refName] = new Chart(chartRef, {
        type: chartRef.type, // Get chart type from ref (e.g., 'bar', 'line')
        data: data,
        options: options
      });
    },
    genomeCompleteChart() {
      const documentStyle = getComputedStyle(document.body);
      const genomecomplete_chart = this.samplesStore.filteredStatistics ? this.samplesStore.filteredStatistics['genomecomplete_chart'] : {}

      return {
        labels: Object.keys(genomecomplete_chart),
        datasets: [
          {
            data: Object.values(genomecomplete_chart),
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
      const _data = this.samplesStore.filteredStatistics ? this.samplesStore.filteredStatistics['lineage_bar_chart'] : {};

      let datasets = [];
      let weeks = [];

      if (_data.length > 0) {

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
      }

      return { labels: weeks, datasets };
    },
    lineage_barChartOptions() {
      return {
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
              callback: function (value) {
                return value + '%'; // Add percentage symbol
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
      const _data = this.samplesStore.filteredStatistics ? this.samplesStore.filteredStatistics['lineage_area_chart'] : {};


      let datasets = [];
      let dates = [];
      if (_data.length > 0) {
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
      }

      // Return the data structure expected by the area chart component
      return { labels: dates, datasets };
    },
    lineage_areaChartOptions() {
      return {
        plugins: {
          legend: {
            display: true,
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
              callback: function (value) {
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
    },
    sequencingTechChartData() {
      const _data = this.samplesStore.filteredStatistics ? this.samplesStore.filteredStatistics['sequencing_tech'] : {};
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
            display: true
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
                enabled: true,
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
    hashString(str: string) {
      let hash = 0;
      for (let i = 0; i < str.length; i++) {
        hash = str.charCodeAt(i) + ((hash << 5) - hash);
      }
      return Math.abs(hash); //* (Math.random() * (10 - 5) + 5);
    },
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
