<template>
  <div class="page-header">
    <!-- todo: div gets converted into pageheader & class gets eaten -->
    <slot></slot>
  </div>
</template>

<script>
import PageHeaderItem from "./PageHeaderItem";

export default {
  name: "PageHeader",
  props: {},
  components: { PageHeaderItem },
  methods: {}
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.page-header {
  flex-grow: 0 !important;
  flex-shrink: 0 !important;
  height: $header-height !important;
  margin-bottom: 0 !important;
  border-bottom: 0 !important;
  border-radius: 0 !important;
  width: calc(100vw - #{$sidebar-width});

  display: flex;
  flex-direction: row;

  background: $gray-200;

  overflow: visib;
}
</style>
