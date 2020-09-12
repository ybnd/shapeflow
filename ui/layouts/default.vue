<template>
  <div class="app">
    <div v-show="!tooSmall" class="app-body">
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
    this.$store.dispatch("schemas/sync"); // todo: is this really the place for this though?
    this.$store.dispatch("settings/sync");
  },
  mounted() {
    window.onunload = unload;
  },
};
</script>
