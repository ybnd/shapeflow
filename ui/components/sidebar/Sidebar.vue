<template>
  <div class="sidebar">
    <SidebarHeader />
    <nav class="sidebar-nav">
      <div class="scroller">
        <draggable
          tag="ul"
          :list="queue"
          @end="handleReorderQueue"
          class="nav-drag nav"
        >
          <template v-for="id in queue">
            <SidebarNavAnalysis v-bind:key="id" v-bind:id="id" />
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
import { mapState } from "vuex";

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
  beforeMount() {
    this.updateQueueFromStore();
    this.interval_update = setInterval(this.updateQueueFromStore, 250);
  },
  methods: {
    handleClick(e) {
      e.preventDefault();
      e.target.parentElement.classList.toggle("open");
    },
    updateQueueFromStore() {
      this.$store.dispatch("analyzers/sync").then(ok => {
        if (ok) {
          this.queue = this.$store.getters["queue/getQueue"];
        } else {
          // Received 404 -> assume server is down, don't sync anymore
          clearInterval(this.interval_update);
        }
      });
    },
    handleReorderQueue() {
      this.$store.commit("queue/setQueue", { queue: this.queue });
    }
  },
  data: () => {
    return {
      queue: [], // local copy of queue
      interval_update: []
    };
  }
};
</script>

<style>
.nav-link {
  cursor: pointer;
}
</style>
