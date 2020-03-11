<template>
  <div class="sidebar">
    <SidebarHeader />
    <nav class="sidebar-nav">
      <div class="scroller">
        <draggable
          tag="ul"
          :list="this.$store.state.analyzers.queue"
          class="nav-drag nav"
        >
          <template v-for="item in this.$store.state.analyzers.queue">
            <!--connect to vuex store-->
            <SidebarNavAnalysis
              v-bind:key="item.id"
              :name="item.name"
              :url="item.url"
              :id="item.id"
              :progress="item.progress"
              :state="item.state"
              :config="item.config"
            />
          </template>
        </draggable>
        <SidebarNewAnalysis />
      </div>
      <slot></slot>
    </nav>
    <SidebarFooter />
  </div>
</template>

<script>
import SidebarFooter from "./SidebarFooter";
import SidebarHeader from "./SidebarHeader";
import SidebarNavDropdown from "./SidebarNavDropdown";
import SidebarNavAnalysis from "./SidebarNavAnalysis";
import SidebarNavAnalysisLink from "./SidebarNavAnalysisLink";
import SidebarNewAnalysis from "./SidebarNewAnalysis";
import SidebarNavLink from "./SidebarNavLink";
import SidebarNavItem from "./SidebarNavItem";

import draggable from "vuedraggable";

export default {
  name: "sidebar",
  components: {
    SidebarFooter,
    SidebarHeader,
    SidebarNavDropdown,
    SidebarNavAnalysis,
    SidebarNavAnalysisLink,
    SidebarNewAnalysis,
    SidebarNavLink,
    SidebarNavItem,
    draggable
  },
  methods: {
    handleClick(e) {
      e.preventDefault();
      e.target.parentElement.classList.toggle("open");
    }
  }
};
</script>

<style>
.nav-link {
  cursor: pointer;
}
</style>
