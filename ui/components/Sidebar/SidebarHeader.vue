<template>
  <header class="sidebar-header">
    <div>
      <SidebarNavLink url="/" name="isimple" class="sidebar-header-link" icon="fa fa-home"/>
    </div>
  </header>
</template>

<script>
  import SidebarNavDropdown from './SidebarNavDropdown';
  import SidebarNavLink from './SidebarNavLink'
  import SidebarNavItem from './SidebarNavItem'

  export default {
    name: 'sidebar-footer',
    class: 'sidebar',
    components: {
      SidebarNavDropdown,
      SidebarNavItem,
      SidebarNavLink,
    },
  }
</script>

<style>
  .sidebar-header-link {
    font-size: 110%;
    font-weight: bold;
    text-align: left;
  }
</style>
