<template>
  <footer class="sidebar-footer">
    <SidebarNavDropdown icon="" name="Application">
      <SidebarNavLink name="Settings" icon="fa fa-cogs" url="/settings" />
      <!--      <SidebarNavLink name="Log" icon="fa fa-file-text-o" url="/log" />-->
      <!--       <SidebarNavLink name="Search" icon="icon-magnifier"/>-->
      <!--       <SidebarNavLink name="Export" icon="fa fa-download"/>-->
      <!--       <SidebarNavLink name="Import" icon="fa fa-upload"/>-->
      <SidebarNavLink name="Tutorial" icon="fa fa-question" url="/tutorial" />
      <SidebarNavLink name="About" icon="fa fa-info" url="/about" />
    </SidebarNavDropdown>
  </footer>
</template>

<script>
import SidebarNavDropdown from "./SidebarNavDropdown";
import SidebarNavLink from "./SidebarNavLink";
import SidebarNavItem from "./SidebarNavItem";

export default {
  name: "sidebar-footer",
  class: "sidebar",
  components: {
    SidebarNavDropdown,
    SidebarNavItem,
    SidebarNavLink
  }
};
</script>

<style scoped></style>
