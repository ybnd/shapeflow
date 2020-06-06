<template>
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button>Export</b-button>
      </PageHeaderItem>
    </PageHeader>
    <ResultChartStack
      container_class="fullpage-result-container"
      result_class="fullpage-result"
    />
  </div>
</template>

<script>
import ResultChartStack from "../../components/results/ResultChartStack";
import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";

export default {
  name: "result",
  components: { PageHeader, PageHeaderItem, ResultChartStack },
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.fullpage-result-container {
  width: calc(100vw - #{$sidebar-width});
  height: calc(100vh - #{$header-height});
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.fullpage-result {
  position: relative;
  flex-shrink: 1;
  flex-basis: 100vh;
  max-height: 100vh;
  min-height: 200px;
  display: flex;
  width: calc(100vw - #{$sidebar-width});
}
.fullpage-result canvas {
  /*flex-grow: 1;*/
  width: calc(100vw - #{$sidebar-width});
}
</style>
