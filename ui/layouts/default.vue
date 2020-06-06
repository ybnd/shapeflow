<template>
  <div class="app">
    <div class="app-body">
      <Sidebar />
      <main class="main">
        <nuxt />
      </main>
    </div>
  </div>
</template>

<script>
import { Sidebar } from "~/components/";

import { unload } from "../static/api";

export default {
  name: "default-layout",
  components: {
    Sidebar,
  },
  mounted() {
    window.onunload = unload;
  },
};
</script>
