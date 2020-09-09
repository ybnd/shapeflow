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
import SidebarNavItem from "./SidebarNavItem";

import { api, ping } from "../../static/api";

export default {
  name: "sidebar-footer",
  class: "sidebar",
  components: {
    SidebarNavDropdown,
    SidebarNavItem,
    SidebarNavLink,
  },
  mounted() {
    this.check_interval = setInterval(this.checkConnection, 1000);
  },
  destroyed() {
    clearInterval(this.check_interval);
  },
  methods: {
    checkConnection() {
      if (
        Date.now() - this.$store.getters["analyzers/getLastBackendContact"] <
        500
      ) {
        this.connected = true;
      } else {
        ping().then((ok) => {
          this.connected = ok;
        });
      }
    },
  },
  computed: {
    restart() {
      return api("restart");
    },
    quit() {
      return api("quit");
    },
  },
  data() {
    return {
      check_interval: null,
      connected: false,
    };
  },
};
</script>

<style scoped lang="scss">
.sidebar-footer {
  padding: 0 !important;
}
</style>
