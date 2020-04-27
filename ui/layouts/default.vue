<template>
  <div class="app">
    <div class="app-body">
      <Sidebar />
      <main class="main">
        <nuxt />
      </main>
    </div>
  </div>
</template>

<script>
import {
  Header as AppHeader,
  Sidebar,
  Aside as AppAside,
  Footer as AppFooter,
  Breadcrumb
} from "~/components/";

export default {
  name: "full",
  components: {
    // AppHeader,
    Sidebar
    // AppAside,
    // AppFooter,
    // Breadcrumb
  },
  data() {
    return {
      previous_id: "",
      previous_path: ""
    };
  },
  mounted() {
    this.highlightCurrent();
  },
  methods: {
    highlightCurrent() {
      if (this.unhighlight) {
        this.$root.$emit(this.unhighlight);
      }

      this.$root.$emit(this.open);
      this.$root.$emit(this.highlight);

      this.previous_id = this.id;
      this.previous_path = this.path;
    }
  },

  watch: {
    $route() {
      this.highlightCurrent();
    }
  },
  computed: {
    id() {
      return this.$route.query.id;
    },
    path() {
      return this.$route.path;
    },
    open() {
      if (this.id) {
        return `event-sidebar-open-${this.id}`;
      } else {
        return "";
      }
    },
    highlight() {
      if (this.path && this.id) {
        return `event-sidebar-highlight-${this.path}?id=${this.id}`;
      } else {
        return "";
      }
    },
    unhighlight() {
      if (this.previous_path && this.previous_id) {
        return `event-sidebar-unhighlight-${this.previous_path}?id=${this.previous_id}`;
      } else {
        return "";
      }
    }
  }
};
</script>
