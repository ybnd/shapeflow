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

$item-height: calc(#{$header-height - 8px});

.page-header-item {
  flex: 0 1 auto;

  padding-top: 4px;
  padding-bottom: 4px;

  background: $gray-200;
  display: block;
  padding-left: $sidebar-nav-link-padding-x;

  overflow: visible;

  height: $item-height;
  min-height: $item-height;
  max-height: $item-height;

  min-width: 20px;
}
.page-header-item .btn {
  height: $item-height;
}
.page-header-item * {
  height: $item-height;
  max-height: $item-height;
}

.header-button-icon {
  width: $item-height;
  font-size: 14px;
  padding-top: 2px;
  padding-bottom: 2px;
  padding-left: 2px;
  padding-right: 2px;
}
</style>
