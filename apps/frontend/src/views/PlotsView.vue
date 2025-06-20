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
            :key="isBarChart"
            :type="isBarChart ? 'bar' : 'line'"
            :data="isBarChart ? lineageBarData() : lineageAreaData()"
            :options="isBarChart ? lineageBarChartOptions() : lineageAreaChartOptions()"
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
      <!-- Property plots -->
      <div v-for="(plot, index) in plots" :key="index" class="panel" style="grid-column: span 2">
        <PrimePanel :header="plot.plotTitle" class="w-full shadow-2">
          <div style="width: 100%; display: flex; justify-content: center">
            <PrimeButton
              icon="pi pi-times"
              class="p-button-danger p-button-rounded"
              style="height: 1.5rem; width: 1.5rem"
              @click="removePropertyPlot(plot)"
            />
            <PrimeChart
              :type="getChartType(plot.type)"
              :data="plot.data"
              :options="plot.options"
              style="width: 100%; height: 25vh"
            />
          </div>
        </PrimePanel>
      </div>
      <!-- + Button for Adding New Property Plots -->
      <div class="add-plot-button">
        <PrimeButton
          label="Add Property Plot"
          icon="pi pi-plus"
          class="p-button-warning"
          @click="showPlotSelectionDialog"
        />
      </div>
    </div>
    <!-- Plot Selection Dialog -->
    <PrimeDialog v-model:visible="plotSelectionDialogVisible" header="Select Plot Type" modal>
      <div style="display: flex; flex-direction: column; gap: 1rem">
        <PrimeDropdown
          v-model="selectedPlotType"
          :options="plotTypes"
          placeholder="Select Plot Type"
          class="w-full"
        />
        <PrimeButton
          label="Next"
          icon="pi pi-arrow-right"
          class="p-button-success"
          :disabled="!selectedPlotType"
          @click="showFeatureSelectionDialog"
        />
      </div>
    </PrimeDialog>

    <!-- Feature Selection Dialog -->
    <PrimeDialog
      v-model:visible="featureSelectionDialogVisible"
      :header="`Select Features for ${selectedPlotType}`"
      modal
    >
      <div style="display: flex; flex-direction: column; gap: 1rem">
        <!-- Conditional rendering based on plot type -->
        <div
          v-if="
            selectedPlotType === 'bar' ||
            selectedPlotType === 'doughnut' ||
            selectedPlotType === 'line'
          "
        >
          <PrimeDropdown
            v-model="selectedProperty"
            :options="samplesStore.metaCoverageOptions"
            placeholder="Select Property"
            class="w-full"
          />
        </div>
        <div v-if="selectedPlotType === 'scatter'">
          <PrimeDropdown
            v-model="selectedXProperty"
            :options="samplesStore.metaCoverageOptions"
            placeholder="Select X-Axis Property"
            class="w-full"
          />
          <PrimeDropdown
            v-model="selectedYProperty"
            :options="samplesStore.metaCoverageOptions"
            placeholder="Select Y-Axis Property"
            class="w-full"
          />
        </div>
        <div v-if="selectedPlotType === 'histogram'">
          <PrimeDropdown
            v-model="selectedProperty"
            :options="samplesStore.metaCoverageOptions"
            placeholder="Select Property"
            class="w-full"
          />
          <PrimeInputNumber
            v-model="selectedBinSize"
            placeholder="Select Bin Size"
            class="w-full"
          />
        </div>
        <PrimeButton
          label="Add Plot"
          icon="pi pi-check"
          class="p-button-success"
          :disabled="!isFeatureSelectionValid"
          @click="addPlot"
        />
      </div>
    </PrimeDialog>
  </div>
</template>

<script lang="ts">
import { useSamplesStore } from '@/stores/samples'
import chroma from 'chroma-js'
import type { ChartOptions, TooltipItem } from 'chart.js'
import PrimeToggleButton from 'primevue/togglebutton'
import PrimeInputNumber from 'primevue/inputnumber'
import {
  PlotType,
  type SimplePlotData,
  type HistogramData,
  type PlotConfig,
  type ScatterPlotData,
} from '@/util/types'

export default {
  name: 'PlotsView',
  components: {
    PrimeToggleButton,
    PrimeInputNumber,
  },
  data() {
    return {
      samplesStore: useSamplesStore(),
      isBarChart: true, // Toggle for lineage chart type
      plots: [] as PlotConfig[],
      plotSelectionDialogVisible: false,
      featureSelectionDialogVisible: false,
      selectedPlotType: null as PlotType | null,
      selectedProperty: null as string | null,
      selectedXProperty: null as string | null,
      selectedYProperty: null as string | null,
      selectedBinSize: null as number | null,
      plotTypes: Object.values(PlotType),
    }
  },
  computed: {
    isFeatureSelectionValid(): boolean {
      if (
        this.selectedPlotType === 'bar' ||
        this.selectedPlotType === 'doughnut' ||
        this.selectedPlotType === 'line'
      ) {
        return !!this.selectedProperty
      }
      if (this.selectedPlotType === 'scatter') {
        return !!this.selectedXProperty && !!this.selectedYProperty
      }
      if (this.selectedPlotType === 'histogram') {
        return !!this.selectedProperty && !!this.selectedBinSize
      }
      return false
    },
  },
  mounted() {
    this.samplesStore.updatePlotSamplesPerWeek()
    this.samplesStore.updatePlotGroupedLineagesPerWeek()
    this.samplesStore.updatePlotMetadataCoverage()
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
    getChartType(type: PlotType | null): string {
      // Map 'histogram' to 'bar', otherwise return the original type
      return type === 'histogram' ? 'bar' : type || ''
    },
    cleanDataAndAddNullSamples(data: { [key: string]: number }) {
      if (!data || typeof data !== 'object') return { labels: [], data: [] }
      const cleanedData = Object.fromEntries(
        Object.entries(data).filter(([key, value]) => key !== 'null' && value !== 0),
      )
      const totalSamples = this.samplesStore.filteredStatistics?.filtered_total_count || 0
      const metadataSamples = Object.values(cleanedData).reduce((sum, count) => sum + count, 0)

      const noneCount = data['None'] || 0
      const noMetadataSamples = totalSamples - metadataSamples + noneCount

      const labels = [...Object.keys(cleanedData)]
      const dataset = [...Object.values(cleanedData)]

      // Add a "Not Reported" category if there are samples without metadata
      if (noMetadataSamples > 0) {
        labels.push('Not Reported')
        dataset.push(noMetadataSamples)
      }
      return { labels, data: dataset }
    },
    removePropertyPlot(plot: PlotConfig) {
      this.plots = this.plots.filter(
        (item) => item.propertyName !== plot.propertyName || item.type !== plot.type,
      )
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
        animation: { duration: 1000 },
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
    customChartOptions(not_display_legend = false, has_axes = true): ChartOptions {
      return {
        animation: { duration: 1000 },
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: !not_display_legend,
            position: 'bottom',
          },
          tooltip: {
            callbacks: {
              label: (context: TooltipItem<'bar' | 'line' | 'doughnut'>) =>
                `${context.parsed.y} ${context.dataset.label}`,
            },
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
        scales: has_axes
          ? {
              x: {
                title: {
                  display: not_display_legend,
                  text: this.selectedProperty || '',
                },
              },
              y: {
                title: {
                  display: not_display_legend,
                  text: 'Number of Samples',
                },
              },
            }
          : {},
      }
    },
    customScatterPlotOptions(
      y_feature: string,
      x_feature: string,
      x_axis_type:
        | 'category'
        | 'linear'
        | 'time'
        | 'logarithmic'
        | 'timeseries'
        | 'radialLinear' = 'category',
      y_axis_type:
        | 'category'
        | 'linear'
        | 'time'
        | 'logarithmic'
        | 'timeseries'
        | 'radialLinear' = 'linear',
    ): ChartOptions {
      return {
        animation: { duration: 1000 },
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
            title: {
              display: true,
              text: y_feature || '',
            },
            position: 'right',
          },
          tooltip: {
            callbacks: {
              title: (context: TooltipItem<'scatter'>[]) => {
                // Use the `x` value from the first data point in the tooltip context, because default behavior uses labels and here labels can occur mltiple times in x-values
                const raw = context[0].raw as { x: string; y: number; category: string }
                return `Date: ${raw.x}`
              },
              label: (context: TooltipItem<'scatter'>) => {
                const raw = context.raw as { x: string; y: number; category: string }
                return `${y_feature}: ${raw.category}, ${x_feature}: ${raw.x}, ${raw.y} samples`
              },
            },
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
            type: x_axis_type,
            title: {
              display: true,
              text: x_feature || '',
            },
          },
          y: {
            type: y_axis_type,
            title: {
              display: true,
              text: 'Number of Samples',
            },
          },
        },
      }
    },
    showPlotSelectionDialog() {
      this.plotSelectionDialogVisible = true
    },
    showFeatureSelectionDialog() {
      this.plotSelectionDialogVisible = false
      this.featureSelectionDialogVisible = true
    },
    async addPlot() {
      const plotData = await this.generatePlotData()
      const plotTitle = this.selectedProperty
        ? this.selectedProperty
        : this.selectedXProperty && this.selectedYProperty
          ? `${this.selectedXProperty} - ${this.selectedYProperty}`
          : ''
      const propertyName =
        this.selectedProperty || `${this.selectedXProperty}_${this.selectedYProperty}`
      const plotConfig: PlotConfig = {
        type: this.selectedPlotType,
        propertyName: propertyName,
        plotTitle: plotTitle,
        data: plotData,
        options: this.generatePlotOptions(),
      }
      this.plots.push(plotConfig)
      this.resetSelections()
    },
    resetSelections() {
      this.featureSelectionDialogVisible = false
      this.selectedPlotType = null
      this.selectedProperty = null
      this.selectedXProperty = null
      this.selectedYProperty = null
      this.selectedBinSize = null
    },
    getHistogramPlotData(property: string, binSize: number): HistogramData {
      const propertyData = this.samplesStore.propertyData[property] || {}
      const minValue = Math.min(...Object.keys(propertyData).map(Number))
      const maxValue = Math.max(...Object.keys(propertyData).map(Number))
      const bins = Array.from(
        { length: Math.ceil((maxValue - minValue) / binSize) },
        (_, i) => minValue + i * binSize,
      )
      const histogramData = bins.map((binStart) => {
        const binEnd = binStart + binSize
        const count = Object.entries(propertyData).reduce((sum, [key, value]) => {
          const length = Number(key)
          return length >= binStart && length < binEnd ? sum + Number(value) : sum
        }, 0)
        return count
      })
      const labels = bins.map((binStart) => `${binStart}-${binStart + binSize - 1}`)
      const color = this.generateColorPalette(1)[0]
      return {
        labels: labels,
        datasets: [
          {
            label: `samples`,
            data: histogramData,
            backgroundColor: color,
            borderColor: chroma(color).darken(1.0).hex(),
            borderWidth: 1.5,
          },
        ],
      }
    },
    getScatterPlotData(xProperty: string, yProperty: string) {
      // scatterData data structure e.g {"2024-09-01": Array[{ILLUMIA:1}, {Nanopore:7}] ... }
      const scatterData = this.samplesStore.propertyScatterData[`${xProperty}_${yProperty}`] || {}
      const labels = Object.keys(scatterData)
      // Determine if x-axis data is a date or categorical
      const isDateFormat = (value: string) => /^\d{4}-\d{2}-\d{2}$/.test(value)
      const xData = labels.map((label) => (isDateFormat(label) ? label : label))
      // Extract y values and unwrap Proxy objects
      const data = labels.flatMap((label, index) => {
        const xValue = xData[index]
        const values = scatterData[label as keyof typeof scatterData]
        return (Array.isArray(values) ? values : []).flatMap((item: Record<string, number>) =>
          Object.entries(item).map(([key, value]) => ({
            x: xValue,
            y: value,
            category: key,
          })),
        )
      })
      const uniqueCategories = [...new Set(data.map((point) => point.category))]
      const colors = this.generateColorPalette(uniqueCategories.length)
      return {
        labels: labels,
        datasets: uniqueCategories.map((category, index) => ({
          label: category, // Chart legend for each category
          data: data
            .filter((point) => point.category === category)
            .map((point) => ({
              x: point.x,
              y: point.y,
              category: point.category,
            })),
          backgroundColor: colors[index], // Assign color for the category
          borderColor: chroma(colors[index]).darken(1.0).hex(),
          borderWidth: 1.5,
          pointRadius: 5,
        })),
      }
    },
    // categorical data in bar and lne charts
    getBarLinePropertyPlotData(property: string) {
      const propertyData = this.samplesStore.propertyData[property] || {}
      if (this.isDataEmpty(propertyData)) {
        return this.emptyChart()
      }
      const cleanedData = this.cleanDataAndAddNullSamples(propertyData)
      const baseColor = this.generateColorPalette(2)[0] // Single color for all bars/points
      const colors = cleanedData.labels.map(
        (label) => (label === 'Not Reported' ? '#cccccc' : baseColor), // Grey for "Not Reported", base color for others
      )
      return {
        labels: cleanedData.labels,
        datasets: [
          {
            label: `samples`,
            data: cleanedData.data,
            backgroundColor: colors,
            borderColor: colors.map((color) => chroma(color).darken(1.5).hex()),
            borderWidth: 1.5,
          },
        ],
      }
    },
    // categorical data in doughnut charts
    getDoughnutPropertyPlotData(property: string) {
      const propertyData = this.samplesStore.propertyData[property] || {}
      if (this.isDataEmpty(propertyData)) {
        return this.emptyChart()
      }
      const cleanedData = this.cleanDataAndAddNullSamples(propertyData)
      const colors = this.generateColorPalette(cleanedData.labels.length)
      if (cleanedData.labels.includes('Not Reported')) {
        colors.pop()
        colors.push('#cccccc') // Add gray color for 'Not Reported'
      }
      return {
        labels: cleanedData.labels,
        datasets: [
          {
            label: `samples`,
            data: cleanedData.data,
            backgroundColor: colors,
            borderColor: colors.map((color) => chroma(color).darken(1.5).hex()),
            borderWidth: 1.5,
          },
        ],
      }
    },

    async generatePlotData(): Promise<
      HistogramData | SimplePlotData | ScatterPlotData | undefined
    > {
      // Fetch data from the server if not already available in samplesStore
      if (
        this.selectedPlotType === 'bar' ||
        this.selectedPlotType === 'doughnut' ||
        this.selectedPlotType === 'line'
      ) {
        if (
          this.selectedProperty &&
          (!this.samplesStore.propertyData ||
            !Object.keys(this.samplesStore.propertyData).includes(this.selectedProperty) ||
            !this.samplesStore.propertyData[this.selectedProperty] ||
            Object.keys(this.samplesStore.propertyData[this.selectedProperty]).length === 0)
        ) {
          await this.samplesStore.updatePlotCustom(this.selectedProperty)
        }
        return this.selectedProperty
          ? this.selectedPlotType === 'bar' || this.selectedPlotType === 'line'
            ? (this.getBarLinePropertyPlotData(this.selectedProperty) as SimplePlotData)
            : this.selectedPlotType === 'doughnut'
              ? (this.getDoughnutPropertyPlotData(this.selectedProperty) as SimplePlotData)
              : undefined
          : undefined
      }

      if (this.selectedPlotType === 'scatter') {
        if (this.selectedXProperty && !this.samplesStore.propertyData[this.selectedXProperty]) {
          if (this.selectedXProperty && this.selectedYProperty) {
            await this.samplesStore.updatePlotScatter(
              this.selectedXProperty,
              this.selectedYProperty,
            )
          }
        }
        return this.selectedXProperty && this.selectedYProperty
          ? (this.getScatterPlotData(
              this.selectedXProperty as string,
              this.selectedYProperty as string,
            ) as ScatterPlotData)
          : undefined
      }

      if (this.selectedPlotType === 'histogram') {
        if (
          this.selectedProperty &&
          (!this.samplesStore.propertyData ||
            !Object.keys(this.samplesStore.propertyData).includes(this.selectedProperty) ||
            !this.samplesStore.propertyData[this.selectedProperty] ||
            Object.keys(this.samplesStore.propertyData[this.selectedProperty]).length === 0)
        ) {
          await this.samplesStore.updatePlotCustom(this.selectedProperty)
        }
        return this.selectedProperty && this.selectedBinSize !== null
          ? (this.getHistogramPlotData(
              this.selectedProperty,
              this.selectedBinSize,
            ) as HistogramData)
          : undefined
      }
    },

    generatePlotOptions() {
      // Generate plot options based on selected plot type
      if (this.selectedPlotType == 'scatter') {
        return this.customScatterPlotOptions(
          this.selectedYProperty ?? '',
          this.selectedXProperty || '',
        )
      } else {
        return this.customChartOptions(
          this.selectedPlotType == 'histogram' ||
            this.selectedPlotType == 'bar' ||
            this.selectedPlotType == 'line',
          this.selectedPlotType !== 'doughnut',
        )
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
