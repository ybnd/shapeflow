<template>
  <div class="sidebar">
    <SidebarHeader />
    <nav class="sidebar-nav">
      <div class="scroller">
        <draggable tag="ul" :list="get_queue()" class="nav-drag nav">
          <template v-for="id in get_queue()">
            <!--connect to vuex store-->
            <SidebarNavAnalysis
              v-bind:key="id"
              :name="get_analyzer(id).config.name"
              :id="id"
              :progress="get_analyzer(id).progress"
              :state="get_analyzer(id).state"
              :config="get_analyzer(id).config"
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
    },
    get_queue() {
      return this.$store.state.analyzers.queue;
    },
    get_analyzer(id) {
      return this.$store.state.analyzers.analyzers[id];
    }
  }
};
</script>

<style>
.nav-link {
  cursor: pointer;
}
</style>
