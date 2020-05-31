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

import { events } from "../../static/events";

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
    this.init();
    this.interval_update = setInterval(this.updateQueue, 100);
    this.interval_sync = setInterval(this.sync, 1000);
  },
  methods: {
    handleClick(e) {
      e.preventDefault();
      e.target.parentElement.classList.toggle("open");
    },
    init() {
      this.$store.dispatch("analyzers/source");
      this.full_sync();
    },
    updateQueue() {
      this.queue = this.$store.getters["analyzers/getQueue"];
    },
    sync() {
      if (!this.waiting) {
        this.waiting = true;
        this.$store.dispatch("analyzers/sync").then(ok => {
          if (ok) {
            this.queue = this.$store.getters["analyzers/getQueue"];
          } else {
            console.warn("backend may be down");
          }
          this.waiting = false;
        });
      } else {
        console.warn("backend may be down");
      }
    },

    full_sync() {
      if (!this.waiting) {
        this.waiting = true;
        this.$store.dispatch("options/sync");
        this.$store.dispatch("analyzers/sync").then(ok => {
          if (ok) {
            this.queue = this.$store.getters["analyzers/getQueue"];
          } else {
            console.warn("backend may be down");
          }
          this.waiting = false;
        });
      } else {
        console.warn("backend may be down");
      }
    },
    handleReorderQueue() {
      this.$store.commit("analyzers/setQueue", { queue: this.queue });
    }
  },
  data: () => {
    return {
      queue: [], // local copy of queue
      interval_update: null,
      interval_sync: null,
      waiting: false
    };
  },
  watch: {
    $route(to, from) {
      this.$root.$emit(events.sidebar.unhighlight(from.fullPath));
      this.$root.$emit(events.sidebar.highlight(to.fullPath));
    }
  }
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.nav-link {
  cursor: pointer;
  color: $gray-100;
}
</style>
