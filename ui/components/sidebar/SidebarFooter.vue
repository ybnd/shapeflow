<template>
  <footer class="sidebar-footer">
    <SidebarNavDropdown icon="" name="Application">
      <SidebarNavLink name="Settings" icon="fa fa-cogs" url="/settings" />
      <SidebarNavLink name="Log" icon="fa fa-file-text-o" url="/log" />
      <SidebarNavLink name="Tutorial" icon="fa fa-question" url="/tutorial" />
      <SidebarNavLink name="About" icon="fa fa-info" url="/about" />
      <SidebarNavLink name="Restart" icon="fa fa-refresh" :url="restart" />
      <SidebarNavLink name="Quit" icon="fa fa-power-off" :url="quit" />
    </SidebarNavDropdown>
  </footer>
</template>

<script>
import SidebarNavDropdown from "./SidebarNavDropdown";
import SidebarNavLink from "./SidebarNavLink";
import SidebarNavItem from "./SidebarNavItem";

import { api } from "../../static/api";

export default {
  name: "sidebar-footer",
  class: "sidebar",
  components: {
    SidebarNavDropdown,
    SidebarNavItem,
    SidebarNavLink,
  },
  computed: {
    restart() {
      return api("restart");
    },
    quit() {
      return api("quit");
    },
  },
};
</script>

<style scoped></style>
