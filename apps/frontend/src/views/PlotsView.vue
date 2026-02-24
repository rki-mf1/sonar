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
        <!-- Zoom toggle (top-right) — wheel zoom disabled by default to avoid accidental zooming while scrolling the page -->
        <div style="display: flex; justify-content: flex-end; margin-bottom: 0.5rem">
          <PrimeToggleButton
            v-model="samplesPerWeekZoomEnabled"
            :on-label="'Zoom ON'"
            :off-label="'Zoom OFF'"
            :on-icon="'pi pi-search-plus'"
            :off-icon="'pi pi-search-minus'"
          />
        </div>
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
            v-if="
              samplesStore.plotGroupedLineagesPerWeek &&
              samplesStore.plotGroupedLineagesPerWeek.length
            "
            ref="lineageChart"
            :key="isBarChart"
            :type="isBarChart ? 'bar' : 'line'"
            :data="isBarChart ? lineageBarData() : lineageAreaData()"
            :options="isBarChart ? lineageBarChartOptions() : lineageAreaChartOptions()"
            style="width: 100%; height: 50vh"
          />
          <div v-else>No lineage data available.</div>
        </div>
        <!-- Week range slider — allows users to select which weeks are visible in the chart -->
        <div v-if="totalLineageWeeks() > 1" style="padding: 1rem 1rem 0 1rem">
          <div
            style="
              display: flex;
              justify-content: space-between;
              align-items: center;
              margin-bottom: 0.5rem;
            "
          >
            <span style="font-size: 0.85rem; color: var(--text-color-secondary)">
              Showing weeks {{ lineageWeekRangeLabels[0] }} — {{ lineageWeekRangeLabels[1] }} ({{
                lineageWeekRange[1] - lineageWeekRange[0] + 1
              }}
              of {{ totalLineageWeeks() }} weeks)
            </span>
            <PrimeButton
              label="Show All"
              class="p-button-text p-button-sm"
              icon="pi pi-arrows-h"
              @click="lineageWeekRange = [0, totalLineageWeeks() - 1]"
            />
          </div>
          <PrimeSlider
            v-model="lineageWeekRange"
            :min="0"
            :max="totalLineageWeeks() - 1"
            range
            style="width: 100%"
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
          <!-- Zoom toggle (top-right) — wheel zoom disabled by default to avoid accidental zooming while scrolling the page -->
          <div style="display: flex; justify-content: flex-end; margin-bottom: 0.5rem">
            <PrimeToggleButton
              v-model="metadataCoverageZoomEnabled"
              :on-label="'Zoom ON'"
              :off-label="'Zoom OFF'"
              :on-icon="'pi pi-search-plus'"
              :off-icon="'pi pi-search-minus'"
            />
          </div>
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
          <!-- Top bar: remove button (left) + zoom toggle (right) -->
          <div
            style="
              display: flex;
              justify-content: space-between;
              align-items: center;
              margin-bottom: 0.5rem;
            "
          >
            <PrimeButton
              icon="pi pi-times"
              class="p-button-danger p-button-rounded"
              style="height: 1.5rem; width: 1.5rem"
              @click="removePropertyPlot(plot)"
            />
            <PrimeToggleButton
              v-model="plot.zoomEnabled"
              :on-label="'Zoom ON'"
              :off-label="'Zoom OFF'"
              :on-icon="'pi pi-search-plus'"
              :off-icon="'pi pi-search-minus'"
            />
          </div>
          <div style="width: 100%; display: flex; justify-content: center">
            <PrimeChart
              :type="getChartType(plot.type)"
              :data="plot.data"
              :options="effectiveCustomPlotOptions(plot)"
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
            placeholder="Select X-Axis Property (Date or Numeric or Categorical)"
            class="w-full"
          />
          <PrimeDropdown
            v-model="selectedYProperty"
            :options="samplesStore.metaCoverageOptions"
            placeholder="Select Y-Axis Property (Categorical)"
            class="w-full"
          />
        </div>
        <div v-if="selectedPlotType === 'histogram'">
          <PrimeDropdown
            v-model="selectedProperty"
            :options="samplesStore.metaCoverageOptions"
            placeholder="Select a Numeric Property"
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
import router from '@/router'
import { useSamplesStore } from '@/stores/samples'
import { decodeDatasetsParam, safeDecodeURIComponent } from '@/util/routeParams'
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
      // Zoom toggle state per chart — wheel zoom is disabled by default to prevent
      // accidental zooming when scrolling the page
      samplesPerWeekZoomEnabled: false,
      metadataCoverageZoomEnabled: false,
      // Lineage chart windowing: default window of 52 weeks from the end.
      // lineageWeekRange is a [start, end] pair of indices into the full weeks array.
      lineageWeekRange: [0, 51] as [number, number],
    }
  },
  computed: {
    selectionKey(): string {
      const { reference_accession, dataset = [] } = this.$route.query
      return JSON.stringify({ reference_accession, dataset })
    },
    /** Returns human-readable week labels (e.g. "2024-W01") for the current slider range */
    lineageWeekRangeLabels(): [string, string] {
      const data = this.samplesStore.plotGroupedLineagesPerWeek || []
      if (!Array.isArray(data) || data.length === 0) return ['—', '—']
      const allWeeks = [...new Set(data.map((item: { week: string }) => item.week))]
      const startLabel = allWeeks[this.lineageWeekRange[0]] || '—'
      const endLabel = allWeeks[this.lineageWeekRange[1]] || '—'
      return [startLabel, endLabel]
    },
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
  watch: {
    selectionKey: {
      immediate: true,
      handler() {
        this.applySelectionFromRoute()
      },
    },
    // Re-initialize the week range slider when lineage data changes (e.g. after filter update)
    'samplesStore.plotGroupedLineagesPerWeek'() {
      this.initLineageWeekRange()
    },
  },
  mounted() {},
  methods: {
    // keep plots in sync with route params
    applySelectionFromRoute() {
      const reference_accession =
        typeof this.$route.query.reference_accession === 'string'
          ? safeDecodeURIComponent(this.$route.query.reference_accession)
          : null
      if (!reference_accession) {
        console.log('Invalid URL: missing reference_accession parameter.')
        router.replace({ name: 'Home' })
        return
      }
      const datasets = decodeDatasetsParam(this.$route.query.dataset)
      this.samplesStore.setDataset(
        this.samplesStore.organism ?? null,
        reference_accession,
        datasets,
      )
      this.loadPlotsData()
    },
    loadPlotsData() {
      this.samplesStore.updateSamples()
      this.samplesStore
        .updateStatistics()
        .then(() => this.samplesStore.updatePropertyOptions())
        .then(() => this.samplesStore.updateSelectedColumns())
      this.samplesStore.updateFilteredStatistics()
      this.samplesStore.updateLineageOptions()
      this.samplesStore.updateSymbolOptions()
      this.samplesStore.updateRepliconAccessionOptions()

      this.samplesStore.updatePlotSamplesPerWeek()
      // After lineage data loads, initialize the week range slider to show the last 52 weeks
      this.samplesStore.updatePlotGroupedLineagesPerWeek().then(() => {
        this.initLineageWeekRange()
      })
      this.samplesStore.updatePlotMetadataCoverage()
    },
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
        Object.entries(data).filter(
          ([key, value]) => key !== 'null' && key !== 'None' && key !== '' && value !== 0,
        ),
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
        ? this.samplesStore.plotSamplesPerWeek
        : {}
      if (this.isDataEmpty(samples_per_week)) {
        return this.emptyChart()
      }
      const labels: string[] = []
      const data: number[] = []
      if (Array.isArray(samples_per_week) && samples_per_week.length > 0) {
        samples_per_week.forEach((item) => {
          if (Array.isArray(item) && item.length === 2) {
            labels.push(item[0])
            data.push(item[1])
          } else {
            console.error('Invalid item format in samples_per_week:', item)
          }
        })
      }
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
              // Wheel zoom is toggled by the user via the zoom button (disabled by default)
              wheel: { enabled: this.samplesPerWeekZoomEnabled },
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

    get_lineage_data() {
      const lineages_per_week = this.samplesStore.plotGroupedLineagesPerWeek || []
      if (!Array.isArray(lineages_per_week) || lineages_per_week.length === 0) {
        console.error('lineages_per_week is undefined or empty')
        return { lineages_per_week: [], lineages: [], colors: [], weeks: [], lookupMap: new Map() }
      }
      let lineages = [...new Set(lineages_per_week.map((item) => item.lineage_group))]
        .filter((l) => l !== null)
        .sort(new Intl.Collator(undefined, { numeric: true, sensitivity: 'base' }).compare) // natural sort: ensure e.g. MC.2 < MC.10

      let colors
      if (lineages.includes('Unknown')) {
        lineages = lineages.filter((l) => l !== 'Unknown')
        lineages.unshift('Unknown')
        colors = this.generateColorPalette(lineages.length - 1)
        colors.unshift('#cccccc') // Add grey color for "Unknown"
      } else {
        colors = this.generateColorPalette(lineages.length)
      }

      const allWeeks = [...new Set(lineages_per_week.map((item) => item.week))]

      // Build lookup map keyed by "week|lineage_group" for fast data access
      const lookupMap = new Map<string, { percentage: number; count: number }>()
      for (const item of lineages_per_week) {
        lookupMap.set(`${item.week}|${item.lineage_group}`, {
          percentage: item.percentage,
          count: item.count,
        })
      }

      // Apply windowing: only show the selected range of weeks
      const maxIndex = allWeeks.length - 1
      const rangeStart = Math.min(this.lineageWeekRange[0], maxIndex)
      const rangeEnd = Math.min(this.lineageWeekRange[1], maxIndex)
      const weeks = allWeeks.slice(rangeStart, rangeEnd + 1)

      // Filter lineages to only those with data in the visible week window,
      // so the legend only shows lineages relevant to the current view
      const visibleLineages: string[] = []
      const visibleColors: string[] = []
      for (let i = 0; i < lineages.length; i++) {
        const lineage = lineages[i]
        const hasData = weeks.some((week) => {
          const entry = lookupMap.get(`${week}|${lineage}`)
          return entry && entry.percentage > 0
        })
        if (hasData) {
          visibleLineages.push(lineage)
          visibleColors.push(colors[i])
        }
      }

      return {
        lineages_per_week,
        lineages: visibleLineages,
        colors: visibleColors,
        weeks,
        lookupMap,
      }
    },

    /** Returns the total number of weeks available in the lineage data (used by the range slider) */
    totalLineageWeeks(): number {
      const data = this.samplesStore.plotGroupedLineagesPerWeek || []
      if (!Array.isArray(data) || data.length === 0) return 0
      return [...new Set(data.map((item) => item.week))].length
    },

    /** Initializes the lineage week range to show the last ~6 months (26 weeks), or all if fewer */
    initLineageWeekRange() {
      const total = this.totalLineageWeeks()
      if (total === 0) return
      const windowSize = Math.min(26, total) // 26 weeks ≈ 6 months
      this.lineageWeekRange = [total - windowSize, total - 1]
    },

    lineageBarData() {
      const { lineages, colors, weeks, lookupMap } = this.get_lineage_data()
      // Use Map lookup for O(1) access instead of .find() per cell
      const datasets = lineages.map((lineage, index) => ({
        label: lineage,
        data: weeks.map((week) => lookupMap.get(`${week}|${lineage}`)?.percentage || 0),
        backgroundColor: colors[index],
        borderColor: chroma(colors[index]).darken(0.5).hex(),
        borderWidth: 1.5,
      }))
      return { labels: weeks, datasets }
    },

    lineageAreaData() {
      const { lineages, colors, weeks, lookupMap } = this.get_lineage_data()

      // Pre-compute total percentage per week for normalization (O(1) per lookup)
      const weekTotals = new Map<string, number>()
      for (const week of weeks) {
        let total = 0
        for (const lineage of lineages) {
          total += lookupMap.get(`${week}|${lineage}`)?.percentage || 0
        }
        weekTotals.set(week, total)
      }

      // Normalize data so that percentages for each week sum up to 100%
      const datasets = lineages.map((lineage, index) => ({
        label: lineage,
        data: weeks.map((week) => {
          const totalPercentage = weekTotals.get(week) || 1
          const lineageData = lookupMap.get(`${week}|${lineage}`)?.percentage || 0
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
      // keep only those properties that have data, i.e. are in this.samplesStore.metaCoverageOptions
      const metadata_coverage = Object.fromEntries(
        Object.entries(this.samplesStore.plotMetadataCoverage?.['metadata_coverage'] || {})
          .filter(([key]) => this.samplesStore.metaCoverageOptions.includes(key))
          .sort(),
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
              // Wheel zoom is toggled by the user via the zoom button (disabled by default)
              wheel: { enabled: this.metadataCoverageZoomEnabled },
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
              label: (context: TooltipItem<'bar' | 'line' | 'doughnut'>) => {
                const value = context.raw
                // const label = context.label || 'Unknown Category';
                return `${value} samples`
              },
            },
          },
          zoom: {
            pan: {
              enabled: true,
              mode: 'x',
            },
            zoom: {
              // Wheel zoom is toggled per-chart by the user via the zoom button (disabled by default)
              wheel: { enabled: false },
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
                // Use the `x` value from the first data point in the tooltip context, because default behavior uses labels and here labels can occur multiple times in x-values
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
              // Wheel zoom is toggled per-chart by the user via the zoom button (disabled by default)
              wheel: { enabled: false },
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
        zoomEnabled: false, // Wheel zoom disabled by default; toggle with button
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
      let propertyData = this.samplesStore.propertyData[property] || {}
      const minValue = Math.min(...Object.keys(propertyData).map(Number))
      const maxValue = Math.max(...Object.keys(propertyData).map(Number))
      const cleanedData = this.cleanDataAndAddNullSamples(propertyData)
      propertyData = cleanedData.labels.reduce(
        (acc, label, index) => {
          if (label !== 'Not Reported') {
            acc[label] = cleanedData.data[index]
          }
          return acc
        },
        {} as { [key: string]: number },
      )
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
      if (cleanedData.labels.includes('Not Reported')) {
        labels.push('Not Reported')
        histogramData.push(cleanedData.data[cleanedData.labels.indexOf('Not Reported')] || 0)
      }
      const baseColor = this.generateColorPalette(2)[0] // Single color for all bars/points
      const colors = labels.map(
        (label) => (label === 'Not Reported' ? '#cccccc' : baseColor), // Grey for "Not Reported", base color for others
      )
      return {
        labels: labels,
        datasets: [
          {
            label: `samples`,
            data: histogramData,
            backgroundColor: colors,
            borderColor: colors.map((c) => chroma(c).darken(1.0).hex()),
            borderWidth: 1.5,
          },
        ],
      }
    },
    getScatterPlotData(xProperty: string, yProperty: string) {
      // scatterData data structure e.g {"2024-09-01": Array[{ILLUMIA:1}, {Nanopore:7}] ... }
      if (this.samplesStore.propertyScatterData[`${xProperty}_${yProperty}`] === undefined) {
        this.samplesStore.updatePlotScatter(xProperty, yProperty)
      }
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
    effectiveCustomPlotOptions(plot: PlotConfig): ChartOptions {
      // Dynamically apply zoom.wheel.enabled based on the plot's toggle state.
      // This avoids mutating the stored options object directly.
      const base = plot.options as ChartOptions & {
        plugins?: { zoom?: { zoom?: { wheel?: { enabled: boolean } } } }
      }
      if (!base?.plugins?.zoom?.zoom) return base
      return {
        ...base,
        plugins: {
          ...base.plugins,
          zoom: {
            ...base.plugins?.zoom,
            zoom: {
              ...base.plugins?.zoom?.zoom,
              wheel: { enabled: plot.zoomEnabled ?? false },
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
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  /* Responsive grid */
  width: 100%;
}

.add-property-button {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 25vh;
}
</style>
