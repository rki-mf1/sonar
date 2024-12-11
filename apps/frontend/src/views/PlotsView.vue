<template>
  <div class="container">
    <!-- seq per week plot-->
    <div class="row">
      <div class="col-lineage">
        <!-- Show Skeleton while loading, and Panel with Bar Chart after loading -->
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="100%" height="250px" />
        <Panel v-else header="Week Calendar" class="w-full shadow-2">
          <div style="height: 100%; width: 100%; display: flex; justify-content: center">
            <Chart
              ref="weekCalendarPlot"
              type="bar"
              :data="samplesPerWeekChart()"
              :options="samplesPerWeekChartOptions()"
              style="width: 100%"
            />
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
            <Chart
              ref="lineageAreaPlot"
              type="line"
              :data="lineage_areaData()"
              :options="lineage_areaChartOptions()"
              style="width: 100%; height: 100%"
            />
          </div>
          <!-- lineage bar plot-->
          <h4>Stacked Bar Plot - Lineage Distribution by Calendar Week</h4>
          <div class="h-26rem plot">
            <Chart
              ref="lineageBarPlot"
              type="bar"
              :data="lineage_barData()"
              :options="lineage_barChartOptions()"
              style="width: 100%; height: 100%"
            />
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
            <Chart
              ref="metaDataPlot"
              type="bar"
              :data="metaDataChart()"
              :options="metaDataChartOptions()"
              style="width: 100%"
            />
          </div>
        </Panel>
      </div>
    </div>

    <div class="row">
      <div v-if="samplesStore.propertyMenuOptions.includes('sequencing_tech')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Sequencing Tech." class="w-full shadow-2">
          <div style="justify-content: center" class="h-20rem">
            <Chart
              type="doughnut"
              :data="sequencingTechChartData()"
              :options="sequencingTechChartOptions()"
              style=""
              class="h-full"
            />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyMenuOptions.includes('genome_completeness')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Genome completeness" class="w-full shadow-2">
          <div style="display: flex; justify-content: center" class="h-20rem plot">
            <Chart
              type="pie"
              :data="genomeCompleteChart()"
              :options="genome_pieChartOptions()"
              style=""
            />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyMenuOptions.includes('sequencing_reason')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Sequencing Reason" class="w-full shadow-2">
          <div class="h-20rem plot">
            <Chart
              type="doughnut"
              :data="sequencingReasonChartData()"
              :options="sequencingReasonChartOptions()"
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
              :data="zipCodeChartData()"
              :options="zipCodeChartOptions()"
              class="w-full h-full"
            />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyMenuOptions.includes('sample_type')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Sample Type" class="w-full shadow-2">
          <div class="h-20rem plot">
            <Chart type="pie" :data="sampleTypeChartData()" :options="sampleTypeChartOptions()" />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyMenuOptions.includes('lab')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Lab" class="w-full shadow-2">
          <div class="h-20rem plot">
            <Chart
              type="bar"
              :data="labChartData()"
              :options="labChartOptions()"
              class="w-full h-full"
            />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyMenuOptions.includes('host')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Host" class="w-full shadow-2">
          <div class="h-20rem plot">
            <Chart
              type="bar"
              :data="hostChartData()"
              :options="hostChartOptions()"
              class="w-full h-full"
            />
          </div>
        </Panel>
      </div>

      <div v-if="samplesStore.propertyMenuOptions.includes('length')" class="col">
        <Skeleton v-if="samplesStore.loading" class="mb-2" width="250px" height="250px" />
        <Panel v-else header="Length" class="w-full shadow-2">
          <div class="h-20rem plot">
            <Chart
              type="bar"
              :data="lengthChartData()"
              :options="lengthChartOptions()"
              style="width: 100%; height: 100%"
            />
            <!-- scatter -->
          </div>
        </Panel>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { useSamplesStore } from '@/stores/samples'
import type { TooltipItem } from 'chart.js'
import chroma from 'chroma-js'
import { Chart, type ChartDataset } from 'chart.js'
import type { CustomPercentageLabelsOptions } from '@/util/types'

// Labels for bar plots, text inside the bar for values > 40%
const percentageLabelPlugin = {
  id: 'customPercentageLabels',
  afterDatasetsDraw(chart: Chart, args: any, options: CustomPercentageLabelsOptions) {
    if (!options.enabled) return

    const ctx = chart.ctx
    const datasets = chart.data.datasets

    datasets.forEach((dataset: ChartDataset, datasetIndex: number) => {
      chart.getDatasetMeta(datasetIndex).data.forEach((bar: any, index: number) => {
        let value = dataset.data[index]
        const percentage = `${value}%`

        const x = bar.x
        if (typeof value === 'string') {
          value = parseFloat(value)
          if (isNaN(value)) return
        }
        if (typeof value !== 'number') return
        const y =
          value < options.threshold
            ? bar.y - 10 // Display above the bar for small values
            : bar.y + bar.height / 2 // Center inside the bar for larger values

        ctx.save()
        ctx.font = '12px Arial'
        ctx.fillStyle = '#000'
        ctx.textAlign = 'center'
        ctx.fillText(percentage, x, y)
        ctx.restore()
      })
    })
  },
}

Chart.register(percentageLabelPlugin)

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
  mounted() {},
  beforeUnmount() {},
  methods: {
    cleanDataAndAddNullSamples(data: { [key: string]: number }) {
      if (!data || typeof data !== 'object') return { labels: [], data: [] }
      const cleanedData = Object.fromEntries(
        Object.entries(data).filter(([key, value]) => key !== 'null' && value !== 0),
      )
      const totalSamples = this.samplesStore.filteredStatistics?.filtered_total_count || 0
      const metadataSamples = Object.values(cleanedData).reduce((sum, count) => sum + count, 0)
      const noMetadataSamples = totalSamples - metadataSamples
      const labels = [...Object.keys(cleanedData)]
      const dataset = [...Object.values(cleanedData)]

      // Add a "Not Reported" category if there are samples without metadata
      if (noMetadataSamples > 0) {
        labels.push('Not Reported')
        dataset.push(noMetadataSamples)
      }
      return { labels, data: dataset }
    },

    generateColorPalette(itemCount: number): string[] {
      return chroma
        .scale(['#00429d', '#00b792', '#ffdb9d', '#fdae61', '#f84959', '#93003a']) // ['#9e0142', '#d53e4f', '#f46d43', '#fdae61', '#fee08b', '#e6f598', '#abdda4', '#66c2a5', '#3288bd', '#5e4fa2']
        .mode('lch') // color mode (lch is perceptually uniform)
        .colors(itemCount) // number of colors
    },
    samplesPerWeekChart() {
      const samples_per_week = this.samplesStore.filteredStatistics
        ? this.samplesStore.filteredStatistics['samples_per_week']
        : {}
      const labels: string[] = []
      const data: number[] = []
      if (samples_per_week && Object.keys(samples_per_week).length > 0) {
        Object.keys(samples_per_week).forEach((key) => {
          labels.push(key)
          data.push(samples_per_week[key])
        })
        return {
          labels: labels,
          datasets: [
            {
              label: 'Samples',
              data: data,
              backgroundColor: this.generateColorPalette(1),
              borderColor: this.generateColorPalette(1).map((color) =>
                chroma(color).darken(1.5).hex(),
              ), // darkened border
              borderWidth: 1,
            },
          ],
        }
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
              borderWidth: 1,
            },
          ],
        }
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
            display: false,
          },
        },
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: {
            ticks: {
              color: textColorSecondary,
            },
            grid: {
              color: surfaceBorder,
            },
          },
          y: {
            beginAtZero: true,
            ticks: {
              color: textColorSecondary,
            },
            grid: {
              color: surfaceBorder,
            },
          },
        },
      }
    },
    lineage_areaData() {
      const _data = this.samplesStore.filteredStatistics
        ? this.samplesStore.filteredStatistics['lineage_area_chart']
        : []
      if (!_data || Object.keys(_data).length === 0) {
        return this.emptyChartData()
      }
      const validData = _data.filter((item) => item.date !== 'None-None' && item.lineage !== null)
      const lineages = [...new Set(validData.map((item) => item.lineage))]
      const dates = [...new Set(validData.map((item) => item.date))].sort()
      const colors = this.generateColorPalette(lineages.length)
      const datasets = lineages.map((lineage, index) => ({
        label: lineage,
        data: dates.map(
          (date) =>
            validData.find((item) => item.date === date && item.lineage === lineage)?.percentage ||
            0,
        ),
        fill: true,
        backgroundColor: colors[index],
        borderColor: chroma(colors[index]).darken(0.5).hex(), // darkened border
        borderWidth: 1,
      }))

      return { labels: dates, datasets }
    },
    lineage_areaChartOptions() {
      return {
        animation: false,
        plugins: {
          legend: {
            display: false,
            position: 'bottom',
          },
          tooltip: {
            enabled: true,
            mode: 'nearest',
            intersect: false,
            callbacks: {
              label: function (tooltipItem: TooltipItem<'line'>) {
                const dataset = tooltipItem.dataset
                const value = tooltipItem.raw as number
                return `${dataset.label}: ${value.toFixed(2)}%`
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
              mode: 'x',
            },
          },
          decimation: {
            enabled: true,
            algorithm: 'lttb',
            samples: 1000,
            threshold: 5,
          },
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
                return value + '%'
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
        : []
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData()
      }
      const lineages = [...new Set(_data.map((item) => item.lineage))]
      const weeks = [...new Set(_data.map((item) => item.week))]
      const colors = this.generateColorPalette(lineages.length)
      const datasets = lineages.map((lineage, index) => ({
        label: lineage,
        data: weeks.map(
          (week) =>
            _data.find((item) => item.week === week && item.lineage === lineage)?.percentage || 0,
        ),
        backgroundColor: colors[index],
        borderColor: chroma(colors[index]).darken(0.5).hex(), // darkened border
        borderWidth: 2,
      }))
      return { labels: weeks, datasets }
    },
    lineage_barChartOptions() {
      return {
        animation: false,
        plugins: {
          legend: { display: true, position: 'bottom' },
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
              mode: 'x',
            },
          },
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
                return value + '%'
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
        Object.entries(this.samplesStore.filteredStatistics?.['meta_data_coverage'] || {}).filter(
          ([key]) => this.samplesStore.metaCoverageOptions.includes(key),
        ),
      )

      const totalCount = this.samplesStore.filteredCount
      const labels = Object.keys(coverage)
      const data = Object.values(coverage).map((value) => ((value / totalCount) * 100).toFixed(2))

      return {
        labels: labels,
        datasets: [
          {
            label: 'Coverage (in %)',
            data: data,
            backgroundColor: this.generateColorPalette(1),
            borderColor: this.generateColorPalette(1).map((color) =>
              chroma(color).darken(1.5).hex(),
            ), // darkened border
            borderWidth: 1,
          },
        ],
      }
    },
    metaDataChartOptions() {
      return {
        animation: false,
        plugins: {
          legend: {
            display: false,
          },
          customPercentageLabels: {
            enabled: true,
            threshold: 40,
          },
        },
        scales: {
          y: {
            beginAtZero: true,
            ticks: {
              callback: function (value: number) {
                return value + '%'
              },
            },
          },
        },
        responsive: true,
        maintainAspectRatio: false,
      }
    },
    genomeCompleteChart() {
      const _data = this.samplesStore.filteredStatistics
        ? this.samplesStore.filteredStatistics['genomecomplete_chart']
        : {}
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData()
      }
      const { labels, data } = this.cleanDataAndAddNullSamples(_data)
      const colors = this.generateColorPalette(labels.length)
      return {
        labels,
        datasets: [
          {
            data,
            backgroundColor: colors,
          },
        ],
      }
    },
    genome_pieChartOptions() {
      const documentStyle = getComputedStyle(document.documentElement)
      const textColor = '#333'
      return {
        animation: false,
        plugins: {
          legend: {
            labels: {
              usePointStyle: true,
              color: textColor,
            },
          },
        },
        responsive: true,
        maintainAspectRatio: false,
      }
    },
    sequencingTechChartData() {
      const _data = this.samplesStore.filteredStatistics
        ? this.samplesStore.filteredStatistics['sequencing_tech']
        : {}
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData()
      }
      const { labels, data } = this.cleanDataAndAddNullSamples(_data)
      const colors = this.generateColorPalette(labels.length)
      return {
        labels,
        datasets: [
          {
            data,
            backgroundColor: colors,
            borderColor: colors.map((color) => chroma(color).darken(1.0).hex()), // darkened border
            borderWidth: 1,
          },
        ],
      }
    },
    sequencingTechChartOptions() {
      return {
        animation: false,
        plugins: {
          legend: {
            display: true,
            position: 'bottom',
          },
        },
        responsive: true,
        maintainAspectRatio: false,
      }
    },
    sequencingReasonChartData() {
      const _data = this.samplesStore.filteredStatistics
        ? this.samplesStore.filteredStatistics['sequencing_reason']
        : {}
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData()
      }
      const { labels, data } = this.cleanDataAndAddNullSamples(_data)
      const colors = this.generateColorPalette(labels.length)
      return {
        labels,
        datasets: [
          {
            data,
            backgroundColor: colors,
            borderColor: colors.map((color) => chroma(color).darken(1.0).hex()), // darkened border
            borderWidth: 1,
          },
        ],
      }
    },
    sequencingReasonChartOptions() {
      return {
        animation: false,
        plugins: {
          legend: {
            display: true,
            position: 'bottom',
          },
        },
        responsive: true,
        maintainAspectRatio: false,
      }
    },
    lengthChartData() {
      const _data = this.samplesStore.filteredStatistics
        ? this.samplesStore.filteredStatistics['length']
        : {}
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData()
      }
      const { labels, data } = this.cleanDataAndAddNullSamples(_data)
      return {
        labels,
        datasets: [
          {
            data,
            backgroundColor: this.generateColorPalette(1),
            borderColor: this.generateColorPalette(1).map((color) =>
              chroma(color).darken(1.0).hex(),
            ), // darkened border
            borderWidth: 1,
          },
        ],
      }
    },
    lengthChartOptions() {
      return {
        plugins: {
          legend: {
            display: false,
          },
        },
        scales: {
          y: {
            beginAtZero: true,
          },
        },
        responsive: true,
        maintainAspectRatio: false,
      }
    },
    hostChartData() {
      const _data = this.samplesStore.filteredStatistics
        ? this.samplesStore.filteredStatistics['host']
        : {}
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData()
      }
      const { labels, data } = this.cleanDataAndAddNullSamples(_data)
      return {
        labels,
        datasets: [
          {
            label: 'Samples',
            data,
            backgroundColor: this.generateColorPalette(1),
            borderColor: this.generateColorPalette(1).map((color) =>
              chroma(color).darken(1.0).hex(),
            ), // darkened border
            borderWidth: 1,
          },
        ],
      }
    },
    hostChartOptions() {
      return {
        animation: false,
        indexAxis: 'y',
        plugins: {
          legend: {
            display: false,
          },
        },
        scales: {
          x: {
            beginAtZero: true,
          },
        },
        responsive: true,
        maintainAspectRatio: false,
      }
    },
    labChartData() {
      const _data = this.samplesStore.filteredStatistics
        ? this.samplesStore.filteredStatistics['lab']
        : {}
      const { labels, data } = this.cleanDataAndAddNullSamples(_data)
      return {
        labels,
        datasets: [
          {
            label: 'Samples',
            data: data,
            backgroundColor: this.generateColorPalette(1),
            borderColor: this.generateColorPalette(1).map((color) =>
              chroma(color).darken(1.0).hex(),
            ), // darkened border
            borderWidth: 1,
          },
        ],
      }
    },
    labChartOptions() {
      return {
        plugins: {
          legend: {
            display: false,
          },
          zoom: {
            zoom: {
              wheel: { enabled: true },
              pinch: { enabled: true },
              mode: 'x',
            },
            pan: {
              enabled: true,
              mode: 'x',
            },
            limits: {
              x: { min: 0, minRange: 10 },
            },
          },
        },
        scales: {
          x: { stacked: true },
          y: { stacked: true, beginAtZero: true },
        },
        responsive: true,
        maintainAspectRatio: false,
      }
    },
    zipCodeChartData() {
      const _data = this.samplesStore.filteredStatistics
        ? this.samplesStore.filteredStatistics['zip_code']
        : {}
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData()
      }
      const { labels, data } = this.cleanDataAndAddNullSamples(_data)
      return {
        labels,
        datasets: [
          {
            label: 'Samples',
            data,
            backgroundColor: this.generateColorPalette(1),
            borderColor: this.generateColorPalette(1).map((color) =>
              chroma(color).darken(1.0).hex(),
            ), // darkened border
            borderWidth: 1,
          },
        ],
      }
    },
    zipCodeChartOptions() {
      return {
        animation: false,
        indexAxis: 'y', // Makes the bar chart horizontal
        plugins: {
          legend: {
            display: false,
          },
          zoom: {
            pan: {
              enabled: true,
              mode: 'yx',
            },
            zoom: {
              wheel: {
                enabled: false,
                speed: 0.5,
              },
              mode: 'xy',
            },
            limits: {
              x: { min: 0, minRange: 10 },
            },
          },
        },
        scales: {
          x: {
            beginAtZero: true,
          },
          y: {
            ticks: {
              autoSkip: false, // Ensure all labels
            },
          },
        },
        responsive: true,
        maintainAspectRatio: false,
      }
    },
    sampleTypeChartData() {
      const _data = this.samplesStore.filteredStatistics
        ? this.samplesStore.filteredStatistics['sample_type']
        : {}
      if (this.isDataEmpty(_data)) {
        return this.emptyChartData()
      }
      const { labels, data } = this.cleanDataAndAddNullSamples(_data)
      const colors = this.generateColorPalette(labels.length)
      return {
        labels,
        datasets: [
          {
            data,
            backgroundColor: colors,
            borderColor: colors.map((color) => chroma(color).darken(1.0).hex()), // darkened border
            borderWidth: 1,
          },
        ],
      }
    },
    sampleTypeChartOptions() {
      return {
        animation: false,
        plugins: {
          legend: {
            display: true,
            position: 'right',
          },
        },
        responsive: true,
        maintainAspectRatio: false,
      }
    },
    emptyChartData(label = 'No data available') {
      return {
        labels: [label],
        datasets: [
          {
            label: 'No data available',
            data: [],
          },
        ],
      }
    },
    isDataEmpty(data: { [key: string]: any }): boolean {
      return (
        !data ||
        Object.keys(data).length === 0 ||
        (Object.keys(data).length === 1 && Object.keys(data)[0] == 'null')
      )
    },
  },
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
