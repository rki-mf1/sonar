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
        <div style="width: 100%; display: flex; justify-content: center">
          <PrimeChart
            type="bar"
            :data="lineagesPerWeekData()"
            :options="lineagesPerWeekOptions()"
            style="width: 100%; height: 50vh"
          />
        </div>
      </PrimePanel>
    </div>

    <div style="display: flex; gap: 1rem; width: 100%">
      <!-- meta data plot-->
      <div class="panel">
        <PrimePanel header="Coverage of Meta Data" class="w-full shadow-2">
          <div style="width: 100%; display: flex; justify-content: center">
            <PrimeChart
              type="bar"
              :data="metaDataCoverageData()"
              :options="metaDataCoverageOptions()"
              style="width: 100%; height: 25vh"
            />
          </div>
        </PrimePanel>
      </div>

      <!-- custom property plot-->
      <div class="panel">
        <PrimePanel header="Distrubtion of Properties" class="w-full shadow-2">
          <div style="width: 25%; display: flex; justify-content: flex-end">
            <PrimeDropdown
              v-model="samplesStore.selectedCustomProperty"
              :options="samplesStore.metaCoverageOptions"
              placeholder="Select a Property"
              class="w-full md:w-56"
              @change="samplesStore.updatePlotCustom"
            />
          </div>
          <div style="width: 100%; display: flex; justify-content: center">
            <PrimeChart
              type="doughnut"
              :data="customPlotData()"
              :options="customPlotOptions()"
              style="width: 100%; height: 25vh"
            />
          </div>
        </PrimePanel>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { useSamplesStore } from '@/stores/samples'
import chroma from 'chroma-js'

export default {
  name: 'PlotsView',
  data() {
    return {
      samplesStore: useSamplesStore(),
    }
  },
  mounted() {
    this.samplesStore.updatePlotSamplesPerWeek()
    this.samplesStore.updatePlotGroupedLineagesPerWeek()
    this.samplesStore.updatePlotMetaDataCoverage()
    this.samplesStore.updatePlotCustom()
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

    lineagesPerWeekData() {
      const lineages_per_week = this.samplesStore.plotGroupedLineagesPerWeek
        ? this.samplesStore.plotGroupedLineagesPerWeek['grouped_lineages_per_week']
        : []
      if (this.isDataEmpty(lineages_per_week)) {
        return this.emptyChart()
      }
      const lineages = [...new Set(lineages_per_week.map((item) => item.lineage_group))]
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
        borderWidth: 2.5,
      }))
      return { labels: weeks, datasets: datasets }
    },
    lineagesPerWeekOptions() {
      return {
        animation: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
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
          tooltip: {
            callbacks: {
              label: (context) => `${context.dataset.label}: ${context.parsed.y}%`,
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
              callback: function (value: number) {
                return value + '%'
              },
            },
          },
        },
      }
    },

    metaDataCoverageData() {
      // keep only those properties that have data, i.e. are in this.samplesStore.propertyTableOptions
      // what about the property 'name' ?? its not in the list, but its always shown in the table
      const meta_data_coverage = Object.fromEntries(
        Object.entries(this.samplesStore.plotMetaDataCoverage?.['meta_data_coverage'] || {}).filter(
          ([key]) => this.samplesStore.metaCoverageOptions.includes(key),
        ),
      )
      if (this.isDataEmpty(meta_data_coverage)) {
        return this.emptyChart()
      }
      const totalCount = this.samplesStore.filteredCount
      const labels = Object.keys(meta_data_coverage)
      const data = Object.values(meta_data_coverage).map((value) =>
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
    metaDataCoverageOptions() {
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
              label: (context) => `${context.dataset.label}: ${context.parsed.y}%`,
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

    customPlotData() {
      const property_data = this.samplesStore.plotCustom
        ? this.samplesStore.plotCustom['custom_property']
        : {}
      if (this.isDataEmpty(property_data)) {
        return this.emptyChart()
      }
      const { labels, data } = this.cleanDataAndAddNullSamples(property_data)
      const colors = this.generateColorPalette(labels.length)
      return {
        labels,
        datasets: [
          {
            data,
            backgroundColor: colors,
            borderColor: colors.map((color) => chroma(color).darken(1.0).hex()),
            borderWidth: 1.5,
          },
        ],
      }
    },
    customPlotOptions() {
      return {
        animation: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: true,
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
  justify-content: center;
  margin-bottom: 1em;
  width: 100%;
}
</style>
