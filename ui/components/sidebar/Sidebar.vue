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
    this.sync();
    this.interval_update = setInterval(this.updateQueue, 100);
    // this.interval_sync = setInterval(this.sync, 5000);
  },
  methods: {
    handleClick(e) {
      e.preventDefault();
      e.target.parentElement.classList.toggle("open");
    },
    updateQueue() {
      this.queue = this.$store.getters["queue/getQueue"];
    },
    sync() {
      if (!this.waiting) {
        this.waiting = true;
        this.$store.dispatch("analyzers/sync").then(ok => {
          if (ok) {
            this.queue = this.$store.getters["queue/getQueue"];
          } else {
            // Received 404 -> assume server is down, don't sync anymore
            clearInterval(this.interval_update);
          }
          this.waiting = false;
        });
      } else {
        console.warn("backend is overwhelmed :(");
      }
    },
    handleReorderQueue() {
      this.$store.commit("queue/setQueue", { queue: this.queue });
    },
    setCurrent(page, id) {
      // todo: open id's dropdown ~ event
      // todo: set id's page link to current ~ event
    }
  },
  data: () => {
    return {
      queue: [], // local copy of queue
      interval_update: null,
      interval_sync: null,
      waiting: false
    };
  }
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.nav-link {
  cursor: pointer;
}
</style>
