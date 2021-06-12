<template>
  <header class="sidebar-header">
    <ul class="sidebar-header-items">
      <li class="nav-link home" @click="handleClick">
        <img id="icon" src="shapeflow-white.svg">&nbsp;shapeflow
      </li>
    </ul>
  </header>
</template>

<script>
export default {
  name: "SidebarHeader",
  methods: {
    handleClick() {
      this.$router.push('/');
    },
  },
}
</script>

<style lang="scss" scoped>
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

$header-button-height: 28px;
$header-button-vpadding: 4px;
$header-button-hpadding: 5px;
$header-icon-width: 26px;

.sidebar-header {
  height: $header-height;
  padding-top: $header-button-vpadding;
  padding-bottom: $header-button-vpadding;
  padding-left: $header-button-hpadding;
  padding-right: $header-button-hpadding;
  margin: 0;

  .home > #icon {
    width: $header-icon-width;
    height: calc(0.787 * #{$header-icon-width});
    margin-top: calc(-0.5 * #{$header-button-vpadding});
    margin-right: calc(-1 * #{$header-button-hpadding});
  }
}
.sidebar-header-items {
  margin: 0;
  padding: 0;
  height: calc(#{$header-height} - 2 * #{$header-button-vpadding});
  display: flex;
  flex-direction: row;
  overflow: hidden;
}

.home {
  padding: $header-button-vpadding;
  height: $header-button-height;
  width: calc(#{$sidebar-width} - 2 * #{$header-button-hpadding});

  color: theme-color("gray-200");
  background: theme-color("gray-700");
  font-family: Hack, monospace;
  font-size: 13px;
  font-weight: bolder;
}
</style>
