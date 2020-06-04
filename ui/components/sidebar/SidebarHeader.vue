<template>
  <header class="sidebar-header">
    <ul class="sidebar-header-items">
      <SidebarHeaderButton
        :link="api('start')"
        :link_payload="{ queue: $store.getters['analyzers/getQueue'] }"
        :enable="
          $store.getters['analyzers/getQueueState'] === QueueState.STOPPED
        "
        icon="fa fa-play"
      />
      <SidebarHeaderButton
        :link="api('stop')"
        :enable="
          $store.getters['analyzers/getQueueState'] !== QueueState.STOPPED
        "
        icon="fa fa-stop"
      />
    </ul>
  </header>
</template>

<script>
import { api, QueueState } from "../../static/api";
import SidebarHeaderButton from "./SidebarHeaderButton";

export default {
  name: "sidebar-header",
  components: {
    SidebarHeaderButton
  },
  data() {
    return {
      api,
      QueueState
    };
  }
};
</script>

<style lang="scss" scoped>
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";
.sidebar-header {
  height: $header-height;
  padding: 0;
  margin: 0;
}
.sidebar-header-items {
  margin: 0;
  padding: 2px;
  height: calc(#{$header-height} - 4px);
  display: flex;
  flex-direction: row;
  overflow: hidden;
}
</style>
