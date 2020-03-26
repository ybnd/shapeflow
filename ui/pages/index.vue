<template>
  <div class="fixed-page">
    <draggable
      tag="ul"
      :list="this.$store.state.queue.queue"
      class="analysis-card-drag"
      handle=".handle"
    >
      <template v-for="id in this.$store.state.queue.queue">
        <AnalysisCard v-bind:key="id" :id="id" />
      </template>
    </draggable>
  </div>
</template>

<script>
// https://github.com/SortableJS/Vue.Draggable/blob/master/example/components/handle.vue

import draggable from "vuedraggable";
import AnalysisCard from "../components/dashboard/AnalysisCard";
import { mapState } from "vuex";

import { ping, unload } from "../static/api";

export default {
  name: "dashboard",
  components: {
    AnalysisCard,
    draggable
  },
  methods: {},
  beforeMount() {
    // ping the backend on load
    window.onload = () => {
      this.$store.dispatch("analyzers/sync");
    };
    // notify the backend on unload
    window.onunload = unload;

    // ping the backend every half second
    // once unload() is called; backend starts listening to ping()
    //   -> if one tab/window is closed, but others remain open,
    //      backend will hear some ping()'s and won't stop serving.
    setInterval(() => {
      this.$store.dispatch("analyzers/sync");
      // this.$forceUpdate(); // https://michaelnthiessen.com/force-re-render/
    }, 250);
    setInterval(() => {
      ping;
    }, 500);
  }
};
</script>

<style>
.analysis-card-drag {
  flex: 1;
  display: flex !important;
  flex-direction: column !important;
  flex-wrap: wrap !important;
  justify-content: flex-start;
  align-content: flex-start;
  margin-left: -36px;
  margin-right: 6px;
  max-height: 100vh;
  max-width: 100vw;
}
</style>
