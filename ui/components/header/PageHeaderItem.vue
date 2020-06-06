<template>
  <div class="page-header-item">
    <slot></slot>
  </div>
</template>

<script>
export default {
  name: "PageHeaderItem",
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
  display: flex;
  padding-left: $sidebar-nav-link-padding-x;

  overflow: visible;

  height: $item-height;
  min-height: $item-height;
  max-height: $item-height;

  min-width: 20px;
}
.page-header-item .btn {
  height: $item-height;
  padding: 4px;
}
.page-header-item * {
  height: $item-height;
  max-height: $item-height;
  margin-right: 4px;
}

.header-button-icon {
  width: $item-height;
  font-size: 14px;
  display: flex;
}
.header-button-icon i {
  max-height: calc(#{$item-height} - 8px);
  max-width: calc(#{$item-height} - 8px);
  margin: 0;
  padding: 0;
  padding-top: 4px;
  flex-shrink: 1;
  flex-grow: 1;
}
</style>
