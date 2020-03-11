<template>
  <div class="fixed-page">
    <draggable tag="ul" :list="this.$store.state.analyzers.queue" class="analysis-card-drag" handle=".handle">
      <template v-for="(item, index) in this.$store.state.analyzers.queue">
        <AnalysisCard
          v-bind:key="item.id"
          :name="item.name"
          :index="index"
          :id="item.id"
          :progress="item.progress"
          :state="item.state"
          :config="item.config"/>
      </template>
    </draggable>
  </div>
</template>

<script>

// https://github.com/SortableJS/Vue.Draggable/blob/master/example/components/handle.vue

import draggable from 'vuedraggable'
import AnalysisCard from '../components/dashboard/AnalysisCard';

import { ping, unload } from '../assets/api'

export default {
  name: 'dashboard',
  components: {
    AnalysisCard,
    draggable,
  },
  beforeMount() {
    // ping the backend on load
    window.onload = ping;
    // notify the backend on unload
    window.onunload = unload;

    // ping the backend every half second
    // once unload() is called; backend starts listening to ping()
    //   -> if one tab/window is closed, but others remain open,
    //      backend will hear some ping()'s and won't stop serving.
    setInterval(ping, 500);
  },
}
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
