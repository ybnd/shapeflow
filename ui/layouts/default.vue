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
  beforeCreate() {
    this.$store.dispatch("schemas/sync");
    this.$store.dispatch("settings/sync");
  },
  mounted() {
    window.onunload = unload;
  },
};
</script>
