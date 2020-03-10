<template>
   <footer class="sidebar-footer">
     <SidebarNavDropdown name="Database">
         <SidebarNavLink name="Search" icon="icon-magnifier"/>
         <SidebarNavLink name="Export" icon="icon-arrow-down"/>
         <SidebarNavLink name="Import" icon="icon-arrow-up"/>
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
