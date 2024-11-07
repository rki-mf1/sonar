<template>
  <div class="content p-4">
    <!-- About Section -->
    <div v-animateonscroll="{ enterClass: 'fadein', leaveClass: 'fadeout' }"
      class="shadow-4 align-center animation-duration-1000 animation-ease-in-out mb-4">
      <Card>
        <template #title>
          <h3 class="text-primary mt-4">About Sonar</h3>
        </template>
        <template #content>
          <p class="m-1">
            <strong>Sonar</strong> is an application to explore and compare metadata from
            SARS-CoV-2 sequences available from our data source.
            Furthermore, we offer an advanced filtering tool that enables more detailed queries. This tool benefits all
            users by facilitating better analysis and research.
          </p>
        </template>
      </Card>
    </div>

    <Panel header="" class="shadow-4 mb-4 w-full">
      <div v-animateonscroll="{ enterClass: 'fadein', leaveClass: 'fadeout' }"
        class="align-center animation-duration-1000 animation-ease-in-out">
        <h3 class="text-primary mt-4">How it works</h3>
        <TabView>
          <TabPanel header="Document I">
            <p class="m-0">
              DATA from RKI
            </p>
          </TabPanel>
          <TabPanel header="Document II">
            <p class="m-0">
              Advanced Filter
            </p>
          </TabPanel>
          <TabPanel header="Document III">
            <p class="m-0">
              PlotsView
            </p>
          </TabPanel>
        </TabView>
      </div>
    </Panel>
    <Splitter style="" class="mb-5 shadow-4 ">
      <SplitterPanel class="flex align-items-center justify-content-center ">
        <!-- Acknowledgements Section -->
        <div v-animateonscroll="{ enterClass: 'fadein', leaveClass: 'fadeout' }"
          class="animation-duration-1000 animation-ease-in-out mb-4">
          <div class="m-2">
            <h3 class="text-primary mt-4">Acknowledgements</h3>
            <p class="m-1">
              We would like to thank all contributors and data providers for making this tool possible. Special thanks
              to our partners and colleagues who helped develop and maintain this application.
            </p>
          </div>

        </div>
      </SplitterPanel>
      <SplitterPanel class="flex align-items-center justify-content-center">
        <!-- Contact Section -->
        <div v-animateonscroll="{ enterClass: 'fadein', leaveClass: 'fadeout' }"
          class="flex align-center animation-duration-1000 animation-ease-in-out">
          <div class="m-2">
            <h3 class="text-primary mt-4">Questions and Feedback</h3>
            <p class="">
              Thank you for using our tool! We would love to get your feedback and improve over time. Please don't
              hesitate
              to
              contact us via email using the following address:
              <a href="mailto:FuchsS@rki.de" class="text-primary font-bold">FuchsS@rki.de</a>
            </p>
          </div>
          <div class="m-2">
            <img src="@/assets/images/undraw_in_the_office_re_jtgc.svg" alt="Contact illustration"
              class="w-full max-w-sm" />
          </div>
        </div>
      </SplitterPanel>
    </Splitter>


  </div>
</template>

<script lang="ts">

export default {
  name: 'AboutView'
}

</script>

<style scoped></style>
