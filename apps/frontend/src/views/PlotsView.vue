<template>
  <div class="container">
    <!-- seq per week plot-->
    <div class="row">
      <div class="col-lineage">
        <!-- Show Skeleton while loading, and Panel with Bar Chart after loading -->
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="100%" height="250px" />
        <Panel v-else header="Week Calendar" class="w-full shadow-2">
          <div style="height: 100%; width: 100%; display: flex; justify-content: center">
            <Chart ref="weekCalendarPlot" type="bar" :data="samplesPerWeekChart()" :options="samplesPerWeekChartOptions()"
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

            <Chart type="line" ref="lineageAreaPlot" 
              :data="lineage_areaData()" 
              :options="lineage_areaChartOptions()"
              style="width: 100%; height: 100%" />
          </div>
          <!-- lineage bar plot-->
          <h4>Stacked Bar Plot - Lineage Distribution by Calendar Week</h4>
          <div class="h-26rem plot">
            <Chart type="bar" ref="lineageBarPlot" 
              :data="lineage_barData()" 
              :options="lineage_barChartOptions()"
              style="width: 100%; height: 100%" />
          </div>
        </Panel>
      </div>
    </div>

    <!-- meta data plot-->
    <div class="row">
      <div class="col-lineage">
        <!-- Show Skeleton while loading, and Panel with Bar Chart after loading -->
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="100%" height="250px" />
        <Panel v-else header="Meta Data Coverage" class="w-full shadow-2">
          <div style="height: 100%; width: 100%; display: flex; justify-content: center">
            <Chart ref="metaDataPlot" type="bar" :data="metaDataChart()" :options="metaDataChartOptions()"
              style="width: 100%" />
          </div>
        </Panel>
      </div>
    </div>

    <div class="row">
      <div v-if="samplesStore.propertyMenuOptions.includes('sequencing_tech')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Sequencing Technology" class="w-full shadow-2" >
          <div style="justify-content: center" class="h-20rem ">
            <Chart 
              type="doughnut" 
              :data="PropertyChartData('sequencing_tech', 'doughnut')" 
              :options="DoughnutAndPieChartOptions()" 
              class="h-full" 
            />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyMenuOptions.includes('genome_completeness')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Genome Completeness" class="w-full shadow-2">
          <div style=" display: flex; justify-content: center" class="h-20rem plot">
            <Chart 
              type="pie" 
              :data="PropertyChartData('genome_completeness', 'pie')" 
              :options="DoughnutAndPieChartOptions()" 
            />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyMenuOptions.includes('sequencing_reason')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Sequencing Reason" class="w-full shadow-2">
          <div class="h-20rem">
            <Chart 
              type="doughnut" 
              :data="PropertyChartData('sequencing_reason','doughnut')" 
              :options="DoughnutAndPieChartOptions()" 
              class="h-full" 
              />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyMenuOptions.includes('zip_code')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Zip Code" class="w-full shadow-2">
          <div class="h-20rem plot">
            <Chart 
              type="bar" 
              :data="PropertyChartData('zip_code','bar')" 
              :options="BarPlotChartOptions('y')" 
              class="w-full h-full" 
          />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyMenuOptions.includes('sample_type')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Sample Type" class="w-full shadow-2">
          <div class="h-20rem">
            <Chart 
              type="pie" 
              :data="PropertyChartData('sample_type','pie')" 
              :options="DoughnutAndPieChartOptions()" 
              class="h-full" 
              />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyMenuOptions.includes('lab')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Lab" class="w-full shadow-2">
          <div class="h-20rem">
            <Chart 
              type="bar" 
              :data="PropertyChartData('lab', 'bar')" 
              :options="BarPlotChartOptions('x')" 
              class="w-full h-full" />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyMenuOptions.includes('host')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Host" class="w-full shadow-2">
          <div class="h-20rem">
            <Chart 
              type="bar" 
              :data="PropertyChartData('host', 'bar')" 
              :options="BarPlotChartOptions('y')" 
              class="w-full h-full" />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyMenuOptions.includes('length')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Length" class="w-full shadow-2">
          <div class="h-20rem">
            <Chart 
              type="bar" 
              :data="HistogrammChartData('length',)" 
              :options="BarPlotChartOptions('x')" 
              class="w-full h-full"
            /> <!-- scatter -->
          </div>
        </Panel>
      </div>

      <div v-for="prop in samplesStore.flexiblePropertyOptions" class="col"> 
        <div>
          <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
          <Panel v-else :header="prop" class="w-full shadow-2">
            <div class="h-20rem">
              <Chart 
                type="doughnut" 
                :data="PropertyChartData(prop, 'doughnut')" 
                :options="DoughnutAndPieChartOptions()"
                class="h-full" 
                 />
            </div>
          </Panel>
        </div>
      </div>

    </div>
  </div>
</template>

<script lang="ts">
import { useSamplesStore } from '@/stores/samples';
import type { FilteredStatisticsKeys } from '@/util/types';
import type { TooltipItem } from 'chart.js';
import chroma from 'chroma-js';
import { Chart } from 'chart.js';


export default {
  name: 'PlotsView',
  data() {
    return {
      samplesStore: useSamplesStore(),
      chartInstances: {},
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
    
    cleanDataAndAddNullSamples(data: { [key: string]: number }) {
      if (!data || typeof data !== 'object') return { labels: [], data: [] };
        const cleanedData = Object.fromEntries(
          Object.entries(data).filter(([key, value]) => key !== "null" && value !== 0 && key)
        );
        const totalSamples = this.samplesStore.filteredStatistics?.filtered_total_count || 0;
        const metadataSamples = Object.values(cleanedData).reduce((sum, count) => sum + count, 0);
        const noMetadataSamples = totalSamples - metadataSamples;
        const labels = [...Object.keys(cleanedData)];
        const dataset = [...Object.values(cleanedData)];
        
        // Add a "Not Reported" category if there are samples without metadata
        if (noMetadataSamples > 0) {
          labels.push('Not Reported');
          dataset.push(noMetadataSamples);
        }
        return { labels, data: dataset }
      },

    generateColorPalette(itemCount: number): string[] {
      return chroma.scale(['#00429d', '#00b792', '#ffdb9d', '#fdae61', '#f84959', '#93003a']) // ['#9e0142', '#d53e4f', '#f46d43', '#fdae61', '#fee08b', '#e6f598', '#abdda4', '#66c2a5', '#3288bd', '#5e4fa2']
        .mode('lch') // color mode (lch is perceptually uniform)
        .colors(itemCount); // number of colors
    },

    generateColorDict(labels: string[], fixedLabels: { [label: string]: string }): [string[], string[]] {
        const fixedColors = { ... fixedLabels, ... { 'Not Reported': '#b0b0b0' }};
        const dynamicLabels = labels.filter(label => !(label in fixedColors));
        const colorPalette: string[] = this.generateColorPalette(dynamicLabels.length);
        const colorDict: { [key: string]: string } = {};
        for (let i = 0; i < dynamicLabels.length; i++) {
          colorDict[dynamicLabels[i]] = colorPalette[i];
        }
        const finalColorDict = {...colorDict, ...fixedColors}

        return [Object.keys(finalColorDict), Object.values(finalColorDict),]
    },

    samplesPerWeekChart() {
      const samples_per_week = this.samplesStore.filteredStatistics
        ? this.samplesStore.filteredStatistics['samples_per_week']
        : {};
      const labels: string[] = [];
      const data: number[] = [];
      if (samples_per_week && Object.keys(samples_per_week).length > 0) {
        Object.keys(samples_per_week).forEach((key) => {
          labels.push(key);
          data.push(samples_per_week[key]);
        });
        return {
          labels: labels,
          datasets: [
            {
              label: 'Samples',
              data: data,
              backgroundColor: this.generateColorPalette(1), 
              borderColor: this.generateColorPalette(1).map(color => chroma(color).darken(1.5).hex()), // darkened border
              borderWidth: 1
            }
          ]
        };
      } else {
        // Return an empty chart structure
        return {
          labels: ['No data available'],
          datasets: [
            {
              label: 'Samples',
              data: [], // no data points
              backgroundColor: 'rgba(249, 115, 22, 0.2)',
              borderColor: 'rgb(249, 115, 22)',
              borderWidth: 1
            }
          ]
        };
      }
    },
    samplesPerWeekChartOptions() {
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
    lineage_areaData() {
      const _data = this.samplesStore.filteredStatistics
        ? this.samplesStore.filteredStatistics['lineage_area_chart']
        : [];
      if (this.isDataEmpty(_data) || !_data || Object.keys(_data).length === 0) {
        return this.emptyChartData();
      }
      const validData = _data.filter(item => item.date !== 'None-None' && item.lineage !== null);
      const lineages = [...new Set(validData.map(item => item.lineage))];
      const dates = [...new Set(validData.map(item => item.date))].sort();
      const colors = this.generateColorPalette(lineages.length);
      const datasets = lineages.map((lineage, index) => ({
        label: lineage,
        data: dates.map(date =>
          validData.find(item => item.date === date && item.lineage === lineage)
            ?.percentage || 0
        ),
        fill: true,
        backgroundColor: colors[index], 
        borderColor: chroma(colors[index]).darken(0.5).hex(), // darkened border
        borderWidth: 1,
      }));

      return { labels: dates, datasets };
    },
    lineage_areaChartOptions() {
      return {
        animation: false,
        plugins: {
          legend: {
            display: false, 
            position: "bottom",
          },
        tooltip: {
          enabled: true,
          mode: 'nearest',
          intersect: false,
          callbacks: {
            label: function (tooltipItem: TooltipItem<'line'>) {
              const dataset = tooltipItem.dataset;
              const value = tooltipItem.raw as number; ;
              return `${dataset.label}: ${value.toFixed(2)}%`;
            },
          },
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
                return value + '%';
              },
            },
          },
        },
        responsive: true,
        maintainAspectRatio: false,
      }
    },
    lineage_barData() {
      const _data = this.samplesStore.filteredStatistics
        ? this.samplesStore.filteredStatistics['lineage_bar_chart']
        : [];
      if (this.isDataEmpty(_data) || !_data || Object.keys(_data).length === 0) {
        return this.emptyChartData();
      }
      const lineages = [...new Set(_data.map(item => item.lineage))];
      const weeks = [...new Set(_data.map(item => item.week))];
      const colors = this.generateColorPalette(lineages.length);
      const datasets = lineages.map((lineage, index) => ({
        label: lineage,
        data: weeks.map(
          week =>
            _data.find(item => item.week === week && item.lineage === lineage)?.percentage || 0
        ),
        backgroundColor: colors[index],
        borderColor: chroma(colors[index]).darken(0.5).hex(), // darkened border
        borderWidth: 2,
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
    metaDataChart() {
      // keep only those properties that have data, i.e. are in this.samplesStore.propertyTableOptions
      // what about the property 'name' ?? its not in the list, but its always shown in the table
      const coverage = Object.fromEntries(
        Object.entries(this.samplesStore.filteredStatistics?.["meta_data_coverage"] || {})
          .filter(([key]) => this.samplesStore.propertyTableOptions.includes(key))
      );

      const totalCount = this.samplesStore.filteredCount;
      const labels = Object.keys(coverage);
      const data = Object.values(coverage).map((value) => ((value / totalCount) * 100).toFixed(2));

      return {
        labels: labels,
        datasets: [
          {
            label: "Coverage (in %)",
            data: data,
            backgroundColor: this.generateColorPalette(1), 
            borderColor: this.generateColorPalette(1).map(color => chroma(color).darken(1.5).hex()), // darkened border
            borderWidth: 1
          }
        ]
      };
    },
    metaDataChartOptions() {
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
          y: {
            beginAtZero: true,
            ticks: {
              callback: function (value: number) {
                return value + '%';
              }
            }
          }
        }
      }
    },
    // Property Data
    PropertyChartData(prop:FilteredStatisticsKeys, plotType:string){
      const _data = this.samplesStore.filteredStatistics ? this.samplesStore.filteredStatistics[prop] : {};
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData();
      }
      let { labels, data } = this.cleanDataAndAddNullSamples(_data);
      let colors: string[];
      if (plotType=="bar"){
        colors = this.generateColorPalette(1);
        }
      else {
        [labels, colors] = this.generateColorDict(labels, {});
        }
            
      return {
        labels,
        datasets: [
          {
            label: 'Sample Number',
            data,
            backgroundColor: colors,
            borderColor: colors.map(color => chroma(color).darken(1.0).hex()), // darkened border
            borderWidth: 1
          }
        ]
      };
    },

    HistogrammChartData(prop:FilteredStatisticsKeys){
      const _data = this.samplesStore.filteredStatistics ? this.samplesStore.filteredStatistics[prop] : {};
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData();
      }
      const { labels, data } = this.cleanDataAndAddNullSamples(_data);
      const numericLabels = labels.map((label) => parseFloat(label)).filter((l) => !isNaN(l));
      const minLength = Math.min(...numericLabels);
      const maxLength = Math.max(...numericLabels);
      const numberOfBins = 20;
      const binSize = Math.ceil((maxLength - minLength) / numberOfBins);
      const bins = Array.from({ length: numberOfBins }, (_, i) => ({
          range: [minLength + i * binSize, minLength + (i + 1) * binSize],
          count: 0,
        }));

      // Populate bins with data
      numericLabels.forEach((label, index) => {
        const value = data[index];
        const binIndex = Math.min(
          Math.floor((label - minLength) / binSize),
          numberOfBins - 1 // Ensure the last bin includes maxLength
        );
        bins[binIndex].count += value;
      });

      // Prepare labels and counts for charting
      const chartLabels = bins.map(
        (bin) => `${Math.floor(bin.range[0])}-${Math.floor(bin.range[1] - 1)}`
      );
      const chartData = bins.map((bin) => bin.count);
      const colors = this.generateColorPalette(1);
      // Return chart-compatible data
      return {
        labels: chartLabels,
        datasets: [
          {
            data: chartData,
            backgroundColor: colors,
            borderColor: colors.map(color => chroma(color).darken(1.0).hex()),
            borderWidth: 1,
          },
        ],
      };
    },

    DoughnutAndPieChartOptions() {
      return {
        animation: false,
        plugins: {
          legend: {
            display: true,
            position: 'bottom',
            labels: {
              // usePointStyle: true,
              color: '#333'
            }
          }
        },
        responsive: true,
        maintainAspectRatio: false,
      };
    },

    BarPlotChartOptions(orientation: string) {
      return {
        animation: false,
        indexAxis: orientation, // y = horizontal
        plugins: {
          legend: {
            display: false
          },
          zoom: {
            zoom: {
            wheel: { enabled: true },
            pinch: { enabled: true },
            mode: orientation,
            },
            pan: {
              enabled: true,
              speed: 0.5,
              mode: orientation,
            },
            limits: {
              x: { min: 0, minRange: 10 },
            },
          }
        },
        scales: {
          x: {
            beginAtZero: true,
            stacked: true ,
          },
          y: {
            stacked: true ,
            ticks: {
              autoSkip: false, // Ensure all labels
            },
          },
        },
        responsive: true,
        maintainAspectRatio: false,
      };
    },
    emptyChartData(label = 'No data available') {
      return {
        labels: [label],
        datasets: [
          {
            label: 'No data available',
            data: [], 
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
  justify-content: space-evenly;
  width: 98%;
}

.col {
  flex: 1 1 25;
  max-width: 25%;
  padding: 0.5rem;
  box-sizing: border-box;
}

.plot {
  display: flex; 
  justify-content: center;
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

.p-panel-header {
  text-align: center;
}

.row:nth-child(1),
.row:nth-child(2) {
  .col {
    flex: 1 1 100%; 
    max-width: 100%;
  }
}
  .row:nth-child(3),
  .row:nth-child(4) {
    .col {
      flex: 1 1 25%; 
      max-width: 25%;
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
      flex: 1 1 90%;
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
