<template>
  <div class="content p-4">
    <!-- About Section -->
    <div v-animateonscroll="{ enterClass: 'fadein', leaveClass: 'fadeout' }"
      class="flex box shadow-4 justify-content-center align-items-center animation-duration-1000 animation-ease-in-out">
      <h1 class="text-center text-primary mb-4">About covSonar Explorer</h1>
      <div class="about-content">
        <p class="m-1">
          At <strong>covSonar Explorer</strong>, we provide an application to explore and compare metadata from COVID-19
          sequences available from our data source.<br>
          Furthermore, we offer an advanced filtering tool that enables more detailed queries. This tool benefits all
          users by facilitating better analysis and research.
        </p>
      </div>
    </div>

    <!-- Acknowledgements Section -->
    <div v-animateonscroll="{ enterClass: 'fadein', leaveClass: 'fadeout' }"
      class=" shadow-4 justify-content-center align-items-center m-2 animation-duration-1000 animation-ease-in-out">
      <Card>
        <template #title>
          <h3 class="text-primary mt-4">Acknowledgements</h3>
        </template>
        <template #content>
          <p class="m-0">
            We would like to thank all contributors and data providers for making this tool possible. Special thanks to
            our partners and colleagues who helped develop and maintain this application.
          </p>
        </template>
      </Card>
    </div>
    <!-- Contact Section -->

    <div v-animateonscroll="{ enterClass: 'fadein', leaveClass: 'fadeout' }"
      class="contact-content flex align-items-center animation-duration-1000 animation-ease-in-out">
      <div>
        <p class="m-2">
          Thank you for using our tool! We would love to get your feedback and improve over time. Please don't
          hesitate to contact us via email using the following address:
          <a href="mailto:FuchsS@rki.de" class="text-primary font-bold">FuchsS@rki.de</a>
        </p>
      </div>
      <div class="m-2">
        <img src="@/assets/images/undraw_in_the_office_re_jtgc.svg" alt="Contact illustration"
          class="w-full max-w-sm" />
      </div>
    </div>
  </div>
</template>

<script lang="ts">

export default {
  name: 'AboutView'
}

</script>

<style scoped></style>
