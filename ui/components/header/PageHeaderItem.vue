<template>
  <div class="page-header-item">
    <slot></slot>
  </div>
</template>

<script>
export default {
  name: "PageHeaderItem"
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.page-header-item {
  flex: 0 1 auto;

  margin-bottom: 7px; /* lame pixel-matching */
  margin-top: 8px;

  background: $gray-200;
  display: block;
  padding-left: $sidebar-nav-link-padding-x;

  overflow: visible;

  height: calc(#{$header-height} - 15px);
  min-height: calc(#{$header-height} - 15px);
  max-height: calc(#{$header-height} - 15px);

  min-width: 80px;
}
.page-header-item .btn {
  height: calc(#{$header-height} - 15px);
}
.page-header-item .slider-container {
  height: calc(#{$header-height} - 15px);
  max-height: calc(#{$header-height} - 15px);
}
.page-header-item .dropdown-item {
  background-color: $gray-100;
}
</style>
