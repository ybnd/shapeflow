<template>
  <header class="sidebar-header">
    <SidebarNavLink name="New analysis..." icon="icon-plus"/>
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
