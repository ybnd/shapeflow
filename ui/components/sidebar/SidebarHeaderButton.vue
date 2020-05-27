<template>
  <div
    class="nav-link sidebar-header-button"
    :class="classList"
    @click="execute"
  >
    <i :class="icon" />
  </div>
</template>

<script>
import { axios } from "../../static/api";

export default {
  name: "SidebarHeaderButton",
  props: {
    link: {
      type: String,
      required: true
    },
    link_payload: {
      type: Object,
      required: false
    },
    enable: {
      type: Boolean,
      required: true
    },
    icon: {
      type: String,
      required: true
    }
  },
  methods: {
    execute() {
      console.log("SidebarHeaderButton.execute()");
      console.log(this.link);
      console.log(this.link_payload);
      axios.post(this.link, this.link_payload);
    }
  },
  computed: {
    classList() {
      return [this.enable ? "enable" : "disable"];
    }
  }
};
</script>

<style scoped lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.sidebar-header-button {
  margin: 4px;
  margin-left: 6px;
  padding: 4px;
  height: 28px;
  width: 28px;

  background: theme-color("gray-700");

  .enable {
  }
  .disable {
    background: theme-color("gray-800");
  }
}
.sidebar-header-button i {
  color: theme-color("gray-300");

  .enable {
  }
  .disable {
    color: theme-color("gray-700");
  }
}
</style>
