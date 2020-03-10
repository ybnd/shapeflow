<template>
   <footer class="sidebar-footer">
     <SidebarNavDropdown name="More stuff" icon = "fa fa-navicon">
<!--         <SidebarNavLink name="Search" icon="icon-magnifier"/>-->
       <SidebarNavLink name="Settings" icon="fa fa-sliders"/>
       <SidebarNavLink name="Log" icon="fa fa-file-text-o"/>
<!--       <SidebarNavLink name="Export" icon="fa fa-download"/>-->
<!--       <SidebarNavLink name="Import" icon="fa fa-upload"/>-->
       <SidebarNavLink name="About" icon="fa fa-info"/>
     </SidebarNavDropdown>
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
