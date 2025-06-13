<template>
  <div class="container">
    <PrimeDialog
      v-model:visible="samplesStore.loading"
      class="flex"
      modal
      :closable="false"
      header="Loading..."
    >
      <ProgressSpinner
        v-if="samplesStore.loading"
        class="flex-1 p-3"
        size="small"
        style="color: whitesmoke"
      />
    </PrimeDialog>

    <!-- sample count plot-->
    <div class="panel">
      <PrimePanel header="Number of Samples per Calendar Week" class="w-full shadow-2">
        <div style="width: 100%; display: flex; justify-content: center">
          <PrimeChart
            type="bar"
            :data="samplesPerWeekData()"
            :options="samplesPerWeekOptions()"
            style="width: 100%; height: 25vh"
          />
        </div>
      </PrimePanel>
    </div>

    <!-- lineage plot-->
    <div class="panel">
      <PrimePanel
        header="Distribution of grouped Lineages per Calendar Week"
        class="w-full shadow-2"
      >
        <!-- Toggle for chart type -->
        <div style="display: flex; justify-content: flex-end; margin-bottom: 1rem">
          <PrimeToggleButton
            v-model="isBarChart"
            :on-label="'Bar Chart'"
            :off-label="'Area Chart'"
            :on-icon="'pi pi-chart-bar'"
            :off-icon="'pi pi-chart-line'"
            class="w-full md:w-56"
          />
        </div>
        <div style="width: 100%; display: flex; justify-content: center">
          <PrimeChart
            ref="lineageChart"
            :type="isBarChart ? 'bar' : 'line'"
            :data="isBarChart ? lineageBarData() : lineageAreaData()"
            :options="isBarChart ? lineageBarChartOptions() : lineageAreaChartOptions()"
            :key="isBarChart"
            style="width: 100%; height: 50vh"
          />
        </div>
      </PrimePanel>
    </div>

    <div
      class="plots-container"
      style="
        display: grid;
        gap: 1rem;
        grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
        width: 100%;
      "
    >
      <div
        class="plots-container"
        style="
          display: grid;
          gap: 1rem;
          grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
          width: 100%;
        "
      >
        <!-- metadata plot-->
        <div class="panel metadata-plot" style="grid-column: span 2">
          <PrimePanel header="Coverage of Metadata" class="w-full shadow-2">
            <div style="width: 100%; display: flex; justify-content: center">
              <PrimeChart
                type="bar"
                :data="metadataCoverageData()"
                :options="metadataCoverageOptions()"
                style="width: 100%; height: 25vh"
              />
            </div>
          </PrimePanel>
        </div>

        <!-- Dynamically added property plots -->
        <div v-for="(property, index) in additionalProperties" :key="index" class="panel">
          <PrimePanel :header="`Distribution of ${property}`" class="w-full shadow-2">
            <template #header>
              <div
                style="
                  display: flex;
                  justify-content: space-between;
                  align-items: center;
                  width: 100%;
                "
              >
                <span style="font-weight: bold">Distribution of {{ property }}</span>
                <PrimeButton
                  icon="pi pi-times"
                  class="p-button-danger p-button-rounded"
                  style="height: 1.5rem; width: 1.5rem"
                  @click="removePropertyPlot(property)"
                />
              </div>
            </template>
            <div style="width: 100%; display: flex; justify-content: center">
              <!-- Show histogram for 'length' property -->
              <PrimeChart
                v-if="
                  property === 'length' ||
                  property === 'zip_code' ||
                  property === 'age' ||
                  property === 'collection_date'
                "
                type="bar"
                :data="customPlotData(property)"
                :options="customPlotOptions(false)"
                style="width: 100%; height: 25vh"
              />
              <!-- Show doughnut chart for other properties -->
              <PrimeChart
                v-else
                type="doughnut"
                :data="customPlotData(property)"
                :options="customPlotOptions(true)"
                style="width: 100%; height: 25vh"
              />
            </div>
          </PrimePanel>
        </div>
        <!-- + Button for Adding New Property Plots -->
        <div class="add-property-button">
          <PrimeButton
            label="Add Property Plot"
            icon="pi pi-plus"
            class="p-button-warning"
            @click="showPropertySelectionDialog"
          />
        </div>
      </div>
      <!-- Property Selection Dialog -->
      <PrimeDialog
        v-model:visible="propertySelectionDialogVisible"
        header="Select a Property"
        modal
      >
        <div style="display: flex; flex-direction: column; gap: 1rem">
          <PrimeDropdown
            v-model="selectedPropertyToAdd"
            :options="samplesStore.metaCoverageOptions"
            placeholder="Select a Property"
            class="w-full"
          />
          <PrimeButton
            label="Add Property Plot"
            icon="pi pi-check"
            class="p-button-success"
            @click="addPropertyPlot"
          />
        </div>
      </PrimeDialog>
    </div>
  </div>
</template>

<script lang="ts">
import { useSamplesStore } from '@/stores/samples'
import chroma from 'chroma-js'
import type { TooltipItem } from 'chart.js'
import PrimeToggleButton from 'primevue/togglebutton'
import { toRaw } from 'vue'
import type { PlotCustom } from '@/util/types'

export default {
  name: 'PlotsView',
  components: {
    PrimeToggleButton,
  },
  data() {
    return {
      samplesStore: useSamplesStore(),
      isBarChart: true, // Toggle for lineage chart type
      propertySelectionDialogVisible: false,
      selectedPropertyToAdd: null,
      additionalProperties: [],
    }
  },
  mounted() {
    this.samplesStore.updatePlotSamplesPerWeek()
    this.samplesStore.updatePlotGroupedLineagesPerWeek()
    this.samplesStore.updatePlotMetadataCoverage()
    this.samplesStore.updatePlotCustom('length')
  },
  methods: {
    isDataEmpty(
      data: { [key: string]: unknown | null } | Array<{ [key: string]: unknown | null }>,
    ): boolean {
      return (
        !data ||
        Object.keys(data).length === 0 ||
        (Object.keys(data).length === 1 && Object.keys(data)[0] == 'null')
      )
    },
    emptyChart() {
      return {
        labels: ['No data available'],
        datasets: [
          {
            label: 'No data available',
            data: [],
          },
        ],
      }
    },
    generateColorPalette(itemCount: number): string[] {
      return chroma
        .scale(['#00429d', '#00b792', '#ffdb9d', '#fdae61', '#f84959', '#93003a'])
        .mode('lch') // color mode (lch is perceptually uniform)
        .colors(itemCount) // number of colors
    },
    cleanDataAndAddNullSamples(data: { [key: string]: number }) {
      if (!data || typeof data !== 'object') return { labels: [], data: [] }
      const cleanedData = Object.fromEntries(
        Object.entries(data).filter(([key, value]) => key !== 'null' && value !== 0),
      )
      const totalSamples = this.samplesStore.filteredStatistics?.filtered_total_count || 0
      const metadataSamples = Object.values(cleanedData).reduce(
        (sum, count) => sum + count,
        0,
      );
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
    removePropertyPlot(property: string) {
      this.additionalProperties = this.additionalProperties.filter((item) => item !== property)
    },

    samplesPerWeekData() {
      const samples_per_week = this.samplesStore.plotSamplesPerWeek
        ? this.samplesStore.plotSamplesPerWeek['samples_per_week']
        : {}
      if (this.isDataEmpty(samples_per_week)) {
        return this.emptyChart()
      }
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
              ),
              borderWidth: 1.5,
            },
          ],
        }
      }
    },
    samplesPerWeekOptions() {
      return {
        animation: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
          zoom: {
            pan: {
              enabled: true,
              mode: 'x',
            },
            zoom: {
              wheel: { enabled: true },
              pinch: { enabled: true },
              mode: 'x',
            },
          },
        },
        scales: {
          x: {
            stacked: true,
            title: {
              display: true,
              text: 'Calendar Week',
            },
          },
        },
      }
    },

    lineageBarData() {
      const lineages_per_week = this.samplesStore.plotGroupedLineagesPerWeek
        ? this.samplesStore.plotGroupedLineagesPerWeek['grouped_lineages_per_week']
        : []
      if (this.isDataEmpty(lineages_per_week)) {
        return this.emptyChart()
      }
      const lineages = [...new Set(lineages_per_week.map((item) => item.lineage_group))]
        .filter((l) => l !== null)
        .sort()
      const weeks = [...new Set(lineages_per_week.map((item) => item.week))]
      const colors = this.generateColorPalette(lineages.length)
      const datasets = lineages.map((lineage, index) => ({
        label: lineage,
        data: weeks.map(
          (week) =>
            lineages_per_week.find((item) => item.week === week && item.lineage_group === lineage)
              ?.percentage || 0,
        ),
        backgroundColor: colors[index],
        borderColor: chroma(colors[index]).darken(0.5).hex(),
        borderWidth: 1.5,
      }))
      return { labels: weeks, datasets }
    },

    lineageAreaData() {
      const lineages_per_week = this.samplesStore.plotGroupedLineagesPerWeek
        ? this.samplesStore.plotGroupedLineagesPerWeek['grouped_lineages_per_week']
        : []
      if (this.isDataEmpty(lineages_per_week)) {
        return this.emptyChart()
      }
      const lineages = [...new Set(lineages_per_week.map((item) => item.lineage_group))]
      const weeks = [...new Set(lineages_per_week.map((item) => item.week))]
      const colors = this.generateColorPalette(lineages.length)
      // Normalize data so that percentages for each week sum up to 100%
      const datasets = lineages.map((lineage, index) => ({
        label: lineage,
        data: weeks.map((week) => {
          const weekData = lineages_per_week.filter((item) => item.week === week)
          const totalPercentage = weekData.reduce((sum, item) => sum + item.percentage, 0)
          const lineageData =
            weekData.find((item) => item.lineage_group === lineage)?.percentage || 0
          return (lineageData / totalPercentage) * 100 // Normalize to 100%
        }),
        borderColor: colors[index],
        backgroundColor: chroma(colors[index]).alpha(0.3).hex(),
        fill: true,
        borderWidth: 2.5,
      }))
      return { labels: weeks, datasets }
    },

    lineageBarChartOptions() {
      return {
        animation: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'bottom',
          },
          tooltip: {
            callbacks: {
              label: (context: TooltipItem<'bar'>) =>
                `${context.dataset.label}: ${context.parsed.y}%`,
            },
          },
        },
        scales: {
          x: {
            stacked: true,
            title: {
              display: true,
              text: 'Calendar Week',
            },
          },
          y: {
            stacked: true,
            min: 0,
            max: 100,
            ticks: {
              callback: (value: number) => `${value}%`,
            },
          },
        },
      }
    },

    lineageAreaChartOptions() {
      return {
        animation: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            position: 'bottom',
          },
        },
        scales: {
          x: {
            title: {
              display: true,
              text: 'Calendar Week',
            },
          },
          y: {
            stacked: true, // Enable stacking
            min: 0,
            max: 100,
            ticks: {
              callback: (value: number) => `${value}%`,
            },
          },
        },
      }
    },

    metadataCoverageData() {
      // keep only those properties that have data, i.e. are in this.samplesStore.propertyTableOptions
      // what about the property 'name' ?? its not in the list, but its always shown in the table
      const metadata_coverage = Object.fromEntries(
        Object.entries(this.samplesStore.plotMetadataCoverage?.['metadata_coverage'] || {}).filter(
          ([key]) => this.samplesStore.metaCoverageOptions.includes(key),
        ),
      )
      if (this.isDataEmpty(metadata_coverage)) {
        return this.emptyChart()
      }
      const totalCount = this.samplesStore.filteredCount
      const labels = Object.keys(metadata_coverage)
      const data = Object.values(metadata_coverage).map((value) =>
        ((value / totalCount) * 100).toFixed(2),
      )
      return {
        labels: labels,
        datasets: [
          {
            label: 'Coverage',
            data: data,
            backgroundColor: this.generateColorPalette(1),
            borderColor: this.generateColorPalette(1).map((color) =>
              chroma(color).darken(1.5).hex(),
            ),
            borderWidth: 1.5,
          },
        ],
      }
    },
    metadataCoverageOptions() {
      return {
        animation: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          },
          zoom: {
            pan: {
              enabled: true,
              mode: 'x',
            },
            zoom: {
              wheel: { enabled: true },
              pinch: { enabled: true },
              mode: 'x',
            },
          },
          tooltip: {
            callbacks: {
              label: (context: TooltipItem<'bar'>) =>
                `${context.dataset.label}: ${context.parsed.y}%`,
            },
          },
        },
        scales: {
          x: {
            title: {
              display: true,
              text: 'Property',
            },
          },
          y: {
            ticks: {
              callback: function (value: number) {
                return value + '%'
              },
            },
          },
        },
      }
    },

    showPropertySelectionDialog() {
      this.propertySelectionDialogVisible = true
    },
    async addPropertyPlot() {
      if (
        this.selectedPropertyToAdd &&
        !this.additionalProperties.includes(this.selectedPropertyToAdd)
      ) {
        this.additionalProperties.push(this.selectedPropertyToAdd)
        await this.samplesStore.updatePlotCustom(this.selectedPropertyToAdd) // Fetch data for the new property
      }
      this.propertySelectionDialogVisible = false
      this.selectedPropertyToAdd = null
    },

    customPlotData(property: string) {
      const property_data = toRaw(this.samplesStore.plotCustom[property] || {})
      if (this.isDataEmpty(property_data)) {
        return this.emptyChart()
      }

      // Generate histogram bins for sequence length
      if (property === 'length') {
        const minLength = Math.min(...Object.keys(property_data).map(Number))
        const maxLength = Math.max(...Object.keys(property_data).map(Number))
        const binSize = Math.ceil((maxLength - minLength) / 20) // Calculate bin size for 20 bars

        const bins = Array.from({ length: 20 }, (_, i) => minLength + i * binSize)

        const histogramData = bins.map((binStart) => {
          const binEnd = binStart + binSize
          const count = Object.entries(property_data).reduce((sum, [key, value]) => {
            const length = Number(key)
            return length >= binStart && length < binEnd ? sum + Number(value) : sum
          }, 0)
          return count
        })

        const labels = bins.map((binStart) => `${binStart}-${binStart + binSize - 1}`)
        const colors = this.generateColorPalette(1)

        return {
          labels,
          datasets: [
            {
              label: 'Sequence Length Distribution',
              data: histogramData,
              backgroundColor: colors,
              borderColor: colors.map((color) => chroma(color).darken(1.0).hex()),
              borderWidth: 1.5,
            },
          ],
        }
      }
      // Default behavior for other properties
      const flattenedData = Object.entries(property_data || {}).reduce((acc, [key, value]) => {
        if (typeof value === 'number') {
          acc[key] = value;
        }
        return acc;
      }, {} as { [key: string]: number });
      const { labels, data } = this.cleanDataAndAddNullSamples(flattenedData);
      const colors = this.generateColorPalette(labels.length)
      if (labels.includes('Not Reported')) {
        colors.pop()
        colors.push('#cccccc') // Add gray color for 'Not Reported'
      }
      return {
        labels: labels,
        datasets: [
          {
            data: data,
            backgroundColor: colors,
            borderColor: colors.map((color) => chroma(color).darken(1.0).hex()),
            borderWidth: 1.5,
          },
        ],
      }
    },

    customPlotOptions(display_legend = true) {
      return {
        animation: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: display_legend,
            position: 'bottom',
          },
          zoom: {
            pan: {
              enabled: true,
              mode: 'x',
            },
            zoom: {
              wheel: { enabled: true },
              pinch: { enabled: true },
              mode: 'x',
            },
          },
        },
      }
    },
  },
}
</script>

<style scoped>
.container {
  display: flex;
  flex-wrap: wrap;
  flex-direction: row;
  overflow-x: auto;
  width: 98%;
}
.panel {
  display: flex;
  flex-wrap: wrap;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  justify-content: center;
  margin-bottom: 1em;
  width: 100%;
}
.plots-container {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr)); /* Responsive grid */
  width: 100%;
}
.add-property-button {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 25vh;
}
</style>
