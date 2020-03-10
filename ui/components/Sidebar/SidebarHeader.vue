<template>
  <header class="sidebar-header">
    <SidebarNavLink name="" icon="fa fa-home"/>
  </header>
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

<style>

</style>
