<template>
   <footer class="sidebar-footer">
     <SidebarNavLink name="Settings" icon="fa fa-cogs" url="/settings"/>
     <SidebarNavLink name="Log" icon="fa fa-file-text-o" url="/log"/>
<!--       <SidebarNavLink name="Search" icon="icon-magnifier"/>-->
<!--       <SidebarNavLink name="Export" icon="fa fa-download"/>-->
<!--       <SidebarNavLink name="Import" icon="fa fa-upload"/>-->
     <SidebarNavLink name="About" icon="fa fa-info" url="/about"/>
   </footer>
</template>

<script>
  import SidebarNavDropdown from './SidebarNavDropdown';
  import SidebarNavLink from './SidebarNavLink'
  import SidebarNavTitle from './SidebarNavTitle'
  import SidebarNavItem from './SidebarNavItem'

export default {
  name: 'sidebar-footer',
  class: 'sidebar',
  components: {
    SidebarNavDropdown,
    SidebarNavTitle,
    SidebarNavItem,
    SidebarNavLink,
  },
}
</script>

<style scoped>
  .sidebar-footer li {
    list-style-type: none;  /*Remove bullet point*/
  }
</style>
