<template>
  <div class="sidebar">
    <SidebarHeader/>
    <nav class="sidebar-nav">
      <div class="scroller">
        <ul class="nav">
          <template v-for="(item) in navItems">   <!--connect to vuex store-->
            <SidebarNavAnalysis
              v-bind:key="item.id"
              :name="item.name"
              :url="item.url"
              :id="item.id"
              :progress="item.progress"
              :state="item.state"
              :config="item.config"/>
          </template>
          <SidebarNewAnalysis/>
        </ul>
      </div>
      <slot></slot>
    </nav>
  <SidebarFooter/>
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
import SidebarNavAnalysisLink from './SidebarNavAnalysisLink';
import SidebarNewAnalysis from './SidebarNewAnalysis';
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
    SidebarMinimizer,
    SidebarNavDivider,
    SidebarNavDropdown,
    SidebarNavAnalysis,
    SidebarNavAnalysisLink,
    SidebarNewAnalysis,
    SidebarNavLink,
    SidebarNavTitle,
    SidebarNavItem,
    SidebarNavLabel
  },
  methods: {
    handleClick (e) {
      e.preventDefault();
      e.target.parentElement.classList.toggle('open')
    },
  }
}
</script>

<style>
  .nav-link {
    cursor:pointer;
  }
</style>
