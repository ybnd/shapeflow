<template>
  <div class="fixed-page">
    <ResultChartStack
      container_class="fullpage-result-container"
      result_class="fullpage-result"
    />
  </div>
</template>

<script>
import ResultChartStack from "../../components/results/ResultChartStack";

export default {
  name: "result",
  components: { ResultChartStack }
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.fullpage-result-container {
  width: calc(100vw - #{$sidebar-width} - 16px);
  height: calc(100vh - 10px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: 8px;
}
.fullpage-result {
  position: relative;
  flex-shrink: 1;
  flex-basis: 100vh;
  max-height: 100vh;
  min-height: 200px;
  display: flex;
  width: calc(100vw - #{$sidebar-width});
  min-width: calc(100vw - #{$sidebar-width});
  max-width: calc(100vw - #{$sidebar-width});
}
.fullpage-result canvas {
  /*flex-grow: 1;*/
  width: calc(100vw - #{$sidebar-width});
}
</style>
