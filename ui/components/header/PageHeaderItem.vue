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

.page-header-item {
  flex: 0 1 auto;

  margin-top: $header-item-gap;
  margin-bottom: $header-item-gap;

  background: $gray-200;
  display: flex;
  padding-left: $sidebar-nav-link-padding-x;

  overflow: visible;

  height: $header-item-height;
  min-height: $header-item-height;
  max-height: $header-item-height;

  min-width: 20px;
}
.page-header-item .btn {
  height: $header-item-height;
  padding: $header-item-gap;
}
.page-header-item > * {
  height: $header-item-height;
  max-height: $header-item-height;
  margin-right: $header-item-gap;
}

.header-button-icon {
  width: $header-item-height;
  font-size: 14px;
  vertical-align: middle;
  padding: 0 !important;
  * {
    max-height: $header-icon-height;
    max-width: $header-icon-height;
    margin: 0;
    padding: 0;
  }
}

.header-text {
  -webkit-user-select: none; /* Safari */
  -moz-user-select: none; /* Firefox */
  -ms-user-select: none; /* IE10+/Edge */
  user-select: none; /* Standard */
}
</style>
