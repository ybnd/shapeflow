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
}
.page-header-item * {
  height: calc(#{$header-height} - 15px);
}
.dropdown-item {
  background-color: $gray-100;
}
</style>
