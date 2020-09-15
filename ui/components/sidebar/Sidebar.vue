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
    <div class="opacity-gradient" />
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
    draggable,
  },
  created() {
    this.$store.dispatch("settings/sync");
    this.$store.dispatch("analyzers/loop");
  },
  destroyed() {
    this.$store.dispatch("analyzers/stop");
  },
  methods: {
    handleClick(e) {
      e.preventDefault();
      e.target.parentElement.classList.toggle("open");
    },
    handleReorderQueue() {
      this.$store.commit("analyzers/setQueue", { queue: this.queue });
    },
  },
  computed: {
    queue: {
      get() {
        console.log("Sidebar.queue.get()");
        const queue = this.$store.getters["analyzers/getQueue"];

        for (const id of queue) {
          console.log(
            `${id} -> ${this.$store.getters["analyzers/getName"](id)}`
          );
        }

        return queue;
      },
      set(q) {
        this.$store.commit("analyzers/setQueue", { queue: q });
      },
    },
  },
  data: () => {
    return {
      interval_update: null,
      interval_sync: null,
      waiting: false,
    };
  },
  watch: {
    $route(to, from) {
      this.$root.$emit(events.sidebar.unhighlight(from.fullPath));
      this.$root.$emit(events.sidebar.highlight(to.fullPath));

      // console.log("to URL:");
      // console.log(to);

      if (to.query.id !== undefined) {
        this.$root.$emit(events.sidebar.open(to.query.id));
      } else if (["/about", "/tutorial", "/settings"].includes(to.fullPath)) {
        // todo: very wonky, should be handled by these urls being in the dropdown in the first place!!
        this.$root.$emit(events.sidebar.open("Application"));
      }
    },
  },
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

$shadow: 24px;

.nav-link {
  cursor: pointer;
  color: $gray-100;
}

.sidebar {
  .opacity-gradient {
    height: $shadow;
    margin-top: -$shadow;
    mix-blend-mode: luminosity;
    background: linear-gradient(transparent, $gray-800);
    pointer-events: none;
  }
}
</style>
