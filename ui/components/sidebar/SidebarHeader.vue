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
      <!-- todo: essentially polling _q_state 3 times, better to keep it in sync ~ store.analyzers -->
      <SidebarHeaderButton
        :link="api('pause')"
        :enable="
          $store.getters['analyzers/getQueueState'] !== QueueState.STOPPED
        "
        icon="fa fa-pause"
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

<style scoped>
.sidebar-header {
  height: 36px;
  padding: 0;
  margin: 0;
}
.sidebar-header-items {
  margin: 0;
  padding: 0;
  height: 36px;
  display: flex;
  flex-direction: row;
  overflow: hidden;
}
</style>
