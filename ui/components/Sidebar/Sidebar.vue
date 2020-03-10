<template>
  <div class="sidebar">
<!--    <SidebarHeader/>-->
<!--    <SidebarForm/>-->
    <SidebarHeader/>
    <nav class="sidebar-nav">
      <div class="scroller">
        <ul class="nav">
          <template v-for="(item) in navItems">
            <SidebarNavAnalysis :name="item.name" :url="item.url" :icon="item.icon" v-bind:key="item.key" :progress="item.progress" :state="item.state"/>
          </template>
          <SidebarNavLink name="New analysis" icon="fa fa-plus"/>
        </ul>
      </div>

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
