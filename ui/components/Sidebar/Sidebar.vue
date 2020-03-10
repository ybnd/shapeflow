<template>
  <div class="sidebar">
<!--    <SidebarHeader/>-->
<!--    <SidebarForm/>-->
    <SidebarHeader/>
    <nav class="sidebar-nav">
      <ul class="nav">
        <template v-for="(item) in navItems">
          <template v-if="item.children">
            <!-- First level dropdown -->
            <SidebarNavAnalysis :name="item.name" :url="item.url" :icon="item.icon" v-bind:key="item.key" :progress="item.progress">
              <template v-for="(childL1) in item.children">
                <!-- eslint-disable -->
                <SidebarNavItem :classes="item.class">
                  <SidebarNavLink :name="childL1.name" :url="childL1.url" :icon="childL1.icon" :badge="childL1.badge" :variant="item.variant"/>
                </SidebarNavItem>
                <!-- eslint-enable -->
              </template>
            </SidebarNavAnalysis>
          </template>
        </template>
      </ul>
      <slot></slot>
    </nav>
    <SidebarFooter/>

<!--    <SidebarMinimizer/>-->
  </div>
</template>
<script>
import SidebarFooter from './SidebarFooter'
import SidebarForm from './SidebarForm'
import SidebarHeader from './SidebarHeader'
import SidebarMinimizer from './SidebarMinimizer'
import SidebarNavDivider from './SidebarNavDivider'
import SidebarNavDropdown from './SidebarNavDropdown'
import SidebarNavAnalysis from './SidebarNavAnalysis'
import SidebarNavLink from './SidebarNavLink'
import SidebarNavTitle from './SidebarNavTitle'
import SidebarNavItem from './SidebarNavItem'
import SidebarNavLabel from './SidebarNavLabel'

export default {
  name: 'sidebar',
  props: {
    navItems: {
      type: Array,
      required: true,
      default: () => []
    }
  },
  components: {
    SidebarFooter,
    // SidebarForm,
    SidebarHeader,
    // SidebarMinimizer,
    SidebarNavDivider,
    SidebarNavDropdown,
    SidebarNavAnalysis,
    SidebarNavLink,
    SidebarNavTitle,
    SidebarNavItem,
    SidebarNavLabel
  },
  methods: {
    handleClick (e) {
      e.preventDefault()
      e.target.parentElement.classList.toggle('open')
    }
  }
}
</script>

<style>
  .nav-link {
    cursor:pointer;
  }
</style>
