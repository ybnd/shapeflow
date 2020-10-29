<template>
  <footer class="sidebar-footer">
    <SidebarNavDropdown
      :icon="connected ? 'fa fa-link' : 'fa fa-spinner fa-spin'"
      name="Application"
      class="application-dropdown"
    >
      <SidebarNavLink name="Settings" icon="fa fa-cogs" url="/settings" />
      <SidebarNavLink name="Log" icon="fa fa-file-text-o" url="/log" />
      <SidebarNavLink name="Restart" icon="fa fa-refresh" :url="restart" />
      <SidebarNavLink name="Quit" icon="fa fa-power-off" :url="quit" />
    </SidebarNavDropdown>
  </footer>
</template>

<script>
import SidebarNavDropdown from "./SidebarNavDropdown";
import SidebarNavLink from "./SidebarNavLink";

import { url } from "../../src/api";

export default {
  name: "sidebar-footer",
  class: "sidebar",
  components: {
    SidebarNavDropdown,
    SidebarNavLink,
  },
  computed: {
    restart() {
      return url("restart");
    },
    quit() {
      return url("quit");
    },
    connected() {
      return this.$store.getters["analyzers/isConnected"];
    },
  },
};
</script>

<style scoped lang="scss">
.sidebar-footer {
  padding: 0 !important;
}
</style>
