<template>
  <div class="fixed-page">
    <draggable
      tag="ul"
      :list="get_queue()"
      class="analysis-card-drag"
      handle=".handle"
    >
      <template v-for="(id, index) in get_queue()">
        <AnalysisCard
          v-bind:key="id"
          :index="index"
          :name="get_analyzers(id).config.name"
          :id="id"
          :progress="get_analyzers(id).progress"
          :state="get_analyzers(id).state"
          :config="get_analyzers(id).config"
        />
      </template>
    </draggable>
  </div>
</template>

<script>
// https://github.com/SortableJS/Vue.Draggable/blob/master/example/components/handle.vue

import draggable from "vuedraggable";
import AnalysisCard from "../components/dashboard/AnalysisCard";
import { mapState } from "vuex";

import { ping, unload } from "../assets/api";

export default {
  name: "dashboard",
  components: {
    AnalysisCard,
    draggable
  },
  computed: mapState({
    queue: state => state.queue
  }),
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
    }, 5000);
    setInterval(() => {
      ping;
    }, 500);
  },
  methods: {
    get_queue() {
      return this.$store.state.analyzers.queue;
    },
    get_analyzer(id) {
      return this.$store.state.analyzers.analyzers[id];
    }
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
