<template>
  <div>
    <template v-if="isTwoStage">
      <div
        :id="id"
        @click="handleShowStageTwo"
        :class="classList"
        class="sidebar-analysis-link"
      >
        <i :class="icon"></i>{{ name }}
        <template v-if="show_popup">
          <b-popover
            :target="id"
            triggers="hover"
            :delay="{ show: 50, hide: 200 }"
            :id="`popover-${id}`"
            :show.sync="show_popup"
            @ok="handleClick"
            container="body"
            placement="right"
            boundary="viewport"
          >
            <b-button variant="primary" @click="handleClickStageTwo">
              <i class="fa fa-check" />
              &nbsp; {{ name }}
            </b-button>
            <b-button variant="danger" @click="handleHideStageTwo">
              <i class="fa fa-times" />
            </b-button>
          </b-popover>
        </template>
      </div>
    </template>
    <template v-else>
      <div
        :id="id"
        @click="handleClick"
        :class="classList"
        class="sidebar-analysis-link"
      >
        <i :class="icon"></i>{{ name }}
      </div>
    </template>
  </div>
</template>

<script>
import axios from "axios";
import { events } from "../../static/events";

export default {
  name: "sidebar-nav-link",
  props: {
    id: {
      // todo: should be called url :/
      type: String,
      required: true,
    },
    name: {
      type: String,
      default: "",
    },
    icon: {
      type: String,
      default: "",
    },
    badge: {
      type: Object,
      default: () => {},
    },
    variant: {
      type: String,
      default: "",
    },
    disabled: {
      type: Boolean,
      default: false,
    },
    enabled: {
      type: Boolean,
      default: true,
    },
  },
  methods: {
    handleClick() {
      if (this.isApiLink) {
        axios.post(this.id);
      } else {
        this.$router.push(this.id);
      }
    },
    handleShowStageTwo() {
      this.show_popup = true;
    },
    handleHideStageTwo() {
      this.show_popup = false;
    },
    handleClickStageTwo() {
      this.$root.$emit(this.id);
      this.handleHideStageTwo();
    },
  },
  created() {
    this.$root.$on(events.sidebar.highlight(this.id), () => {
      this.highlight = true;
    });
    this.$root.$on(events.sidebar.unhighlight(this.id), () => {
      this.highlight = false;
    });
    this.handleHideStageTwo();
  },
  computed: {
    classList() {
      // console.log(`${this.id} - ${this.name} -> disabled = ${this.disabled}`);

      return [
        "nav-link",
        this.highlight ? "highlight" : "",
        this.disabled || !this.enabled ? "disabled" : "",
        this.linkVariant,
      ];
    },
    linkVariant() {
      return this.variant ? `nav-link-${this.variant}` : "";
    },
    isApiLink() {
      return this.id.substring(0, 4) === "/api";
    },
    isTwoStage() {
      return this.id.substring(0, 7) === "sidebar"; // todo: very shitty way to distinguish link type :)
    },
  },
  data() {
    return {
      show_popup: false,
      highlight: false,
    };
  },
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.popover {
  z-index: 9000;
}

.highlight {
  background: $gray-700 !important;
  /*color: $gray-800 !important;*/
  /*font-weight: bold;*/
  //pointer-events: none;
  i {
    color: theme-color("primary") !important;
  }
}

.disabled {
  color: $gray-600 !important; /* todo: copied from CSS output; find theme equivalent! */
  i {
    color: $gray-600 !important;
  }
}

.sidebar-analysis-link {
  font-size: 85%;
}
</style>
