<template>
  <div class="page-content p-3 md:p-5">
    <!-- About Section -->
    <div class="shadow-4 mb-4">
      <PrimeCard>
        <template #title>
          <h3 class="text-primary mt-4">About Sonar</h3>
        </template>
        <template #content>
          <p class="m-1 line-height-3">
            <strong>Sonar</strong> is an open-source genomic surveillance platform that provides an
            end-to-end workflow, from raw consensus sequences to analysis-ready mutation and
            annotation profiles. Sonar is available at
            <a
              href="https://github.com/rki-mf1/sonar"
              target="_blank"
              rel="noopener noreferrer"
              class="text-primary font-bold"
              >github.com/rki-mf1/sonar</a
            >
            under the open-source AGPL-3.0 license.
          </p>
        </template>
      </PrimeCard>
    </div>

    <!-- How it works Section -->
    <PrimePanel header="" class="shadow-4 mb-4 w-full">
      <div>
        <h3 class="text-primary mt-4">How it works</h3>
        <TabView>
          <!-- Document I: Home Page -->
          <TabPanel header="The Home Page">
            <div class="flex flex-column gap-3 p-2 md:p-4">
              <div>
                <h4 class="text-primary mt-0 mb-2">Home Page — Select Your Dataset</h4>
                <p class="m-0 line-height-3">
                  When you open the application, you will be presented with the Home page. Here you
                  can select your target <strong>Organism</strong>, choose the
                  <strong>Reference Accession ID</strong>, and specify the
                  <strong>data source</strong> you want to explore. Once your dataset is configured,
                  click to proceed to the analysis view.
                </p>
              </div>
              <img
                src="@/assets/about-page/home-select-dataset.png"
                alt="Home page — select organism, reference accession, and data source"
                class="doc-image"
              />
            </div>
          </TabPanel>

          <!-- Document II: Table Page -->
          <TabPanel header="Data Table View">
            <div class="flex flex-column gap-5 p-2 md:p-4">
              <!-- Block 1: Sample list -->
              <div class="flex flex-column gap-3">
                <div>
                  <h4 class="text-primary mt-0 mb-2">Table View — Sample List</h4>
                  <p class="m-0 line-height-3">
                    After selecting your dataset, the Table View is the first page you will see. It
                    displays all samples in a sortable, paginated table. You can export the data
                    using the <strong>Export</strong> button, or click on any row to view detailed
                    information for that individual sample.
                  </p>
                </div>
                <img
                  src="@/assets/about-page/table-2-table-list.png"
                  alt="Table view showing the full list of samples"
                  class="doc-image"
                />
              </div>

              <!-- Block 2: Sample detail -->
              <div class="flex flex-column gap-3">
                <div>
                  <h4 class="text-primary mt-0 mb-2">Sample Detail</h4>
                  <p class="m-0 line-height-3">
                    Clicking on a sample row opens a detailed view of that sample, showing all
                    available metadata and genomic profile information.
                  </p>
                </div>
                <img
                  src="@/assets/about-page/table-3-sample-select.png"
                  alt="Sample detail view after clicking a row"
                  class="doc-image"
                />
              </div>

              <!-- Block 3: Filter bar -->
              <div class="flex flex-column gap-3">
                <div>
                  <h4 class="text-primary mt-0 mb-2">Filter Bar</h4>
                  <p class="m-0 line-height-3">
                    The top of the Table View contains a filter bar for quick data filtering.
                    Available filters include: <strong>Sample Collection Time Range</strong>,
                    <strong>Lineage</strong>, and <strong>DNA or Amino Acid Profiles</strong>. A
                    counter on the side shows how many samples currently match your active filters.
                  </p>
                </div>
                <img
                  src="@/assets/about-page/table-4-filter-bar.png"
                  alt="Filter bar with collection time range, lineage, and profile filters"
                  class="doc-image"
                />
              </div>

              <!-- Block 4: Advanced filters -->
              <div class="flex flex-column gap-3">
                <div>
                  <h4 class="text-primary mt-0 mb-2">Advanced Filters</h4>
                  <p class="m-0 line-height-3">
                    For more complex queries, the Advanced Filter panel allows you to filter by any
                    property stored in the database. It supports logical operators (<strong
                      >AND / OR / Group</strong
                    >) and inclusion/exclusion logic, enabling you to build arbitrarily complex
                    filter expressions.
                  </p>
                </div>
                <img
                  src="@/assets/about-page/table-5-adv-filter-bar.png"
                  alt="Advanced filter panel with AND/OR/Group logic operators"
                  class="doc-image"
                />
              </div>
            </div>
          </TabPanel>

          <!-- Document III: Graph Page -->
          <TabPanel header="Plot View">
            <div class="flex flex-column gap-5 p-2 md:p-4">
              <!-- Block 1: Graph overview -->
              <div class="flex flex-column gap-3">
                <div>
                  <h4 class="text-primary mt-0 mb-2">Graph Page — Visualization Overview</h4>
                  <p class="m-0 line-height-3">
                    The Graph page visualizes your filtered dataset as interactive charts. All
                    filter features from the Table View remain available, so you can refine what
                    data is displayed in the graphs.
                  </p>
                </div>
                <img
                  src="@/assets/about-page/plot-1-page.png"
                  alt="Graph page overview with interactive charts"
                  class="doc-image"
                />
              </div>

              <!-- Block 2: Number of samples -->
              <div class="flex flex-column gap-3">
                <div>
                  <h4 class="text-primary mt-0 mb-2">Number of Samples per Calendar Week</h4>
                  <p class="m-0 line-height-3">
                    This default chart shows the total count of samples collected per calendar week,
                    giving you a clear picture of sequencing activity over time. You can interact
                    with and resize the chart as needed.
                  </p>
                </div>
                <img
                  src="@/assets/about-page/plot-2-numberofsample.png"
                  alt="Bar chart showing number of samples per calendar week"
                  class="doc-image"
                />
              </div>

              <!-- Block 3: Lineage distribution -->
              <div class="flex flex-column gap-3">
                <div>
                  <h4 class="text-primary mt-0 mb-2">
                    Distribution of Grouped Lineages per Calendar Week
                  </h4>
                  <p class="m-0 line-height-3">
                    This default stacked chart shows how lineages are distributed across calendar
                    weeks, helping you track the spread and dominance of specific variants over
                    time.
                  </p>
                </div>
                <img
                  src="@/assets/about-page/plot-2-distribution.png"
                  alt="Stacked chart showing distribution of lineages per calendar week"
                  class="doc-image"
                />
              </div>

              <!-- Block 4: Custom graph -->
              <div class="flex flex-column gap-3">
                <div>
                  <h4 class="text-primary mt-0 mb-2">Customize Your Own Graph</h4>
                  <p class="m-0 line-height-3">
                    Beyond the default charts, you can create custom graphs from any data fields
                    available in the database. This gives you full flexibility to generate
                    visualizations suited to your specific analysis or reporting needs.
                  </p>
                </div>
                <img
                  src="@/assets/about-page/plot-3-create-graph.png"
                  alt="Custom graph creation interface"
                  class="doc-image"
                />
              </div>
            </div>
          </TabPanel>
        </TabView>
      </div>
    </PrimePanel>

    <!-- Acknowledgements + Questions and Feedback: responsive two-column layout -->
    <div class="surface-card border-round shadow-4 mb-5 overflow-hidden">
      <div class="flex flex-column md:flex-row">
        <!-- Acknowledgements -->
        <div class="flex-1 p-4 section-left">
          <h3 class="text-primary mt-0">Acknowledgements</h3>
          <p class="m-0 line-height-3">
            This work is supported by a BMWK grant (DAKI-FWS, 01MK21009E) as well as the de.NBI
            Cloud within the German Network for Bioinformatics Infrastructure (de.NBI) and
            ELIXIR-DE.
          </p>
        </div>

        <!-- Questions and Feedback -->
        <div class="flex-1 p-4 t">
          <div class="flex flex-column sm:flex-row align-items-center gap-4">
            <div class="flex-1">
              <h3 class="text-primary mt-0">Questions and Feedback</h3>
              <p class="m-0 line-height-3">
                Thank you for using our tool! We would love to get your feedback and improve over
                time. Please don't hesitate to contact us via email:
                <a href="mailto:huskam@rki.de" class="text-primary font-bold">huskam@rki.de</a>
                or leave us a ticket at
                <a
                  href="https://github.com/rki-mf1/sonar/issues"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-primary font-bold"
                  >github.com/rki-mf1/sonar/issues</a
                >.
              </p>
            </div>
            <img
              src="@/assets/images/undraw_in_the_office_re_jtgc.svg"
              alt="Contact illustration"
              class="contact-illustration"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
export default {
  name: 'AboutView',
}
</script>

<style scoped>
.page-content {
  max-width: 1400px;
  margin-left: auto;
  margin-right: auto;
}

.doc-image {
  width: 100%;
  max-width: 900px;
  display: block;
  margin-left: auto;
  margin-right: auto;
  border-radius: 6px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
}

.contact-illustration {
  width: 120px;
  flex-shrink: 0;
}

.section-left {
  border-bottom: 1px solid var(--surface-border);
}

@media (min-width: 768px) {
  .section-left {
    border-bottom: none;
    border-right: 1px solid var(--surface-border);
  }

  .contact-illustration {
    width: 160px;
  }
}
</style>
