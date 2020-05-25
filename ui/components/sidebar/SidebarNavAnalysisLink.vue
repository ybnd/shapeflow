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
            :id="`popover-${id}`"
            :show.sync="show_popup"
            @ok="doRequest"
            container="body"
            placement="right"
            boundary="viewport"
          >
            <b-button variant="primary" @click="handleClickStageTwo">
              <i class="fa fa-check" />{{ name }}
            </b-button>
            <b-button variant="danger" @click="handleHideStageTwo">
              <i class="fa fa-times" />
            </b-button>
          </b-popover>
        </template>
      </div>
    </template>
    <template v-else-if="isApiLink">
      <div
        :id="id"
        @click="doRequest"
        :class="classList"
        class="sidebar-analysis-link"
      >
        <i :class="icon"></i>{{ name }}
      </div>
    </template>
    <template v-else>
      <div
        :id="id"
        @click="doNavigate"
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
      type: String,
      required: true
    },
    name: {
      type: String,
      default: ""
    },
    icon: {
      type: String,
      default: ""
    },
    badge: {
      type: Object,
      default: () => {}
    },
    variant: {
      type: String,
      default: ""
    }
  },
  methods: {
    doNavigate() {
      // id should be set to the api
      this.$router.push(this.id);
    },
    doRequest(rl) {
      // id should be set to the api
      axios.post(this.id);
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
    }
  },
  beforeMount() {
    this.$root.$on(events.sidebar.highlight(this.id), () => {
      console.log(`${this.id} got highlight event`);
      this.highlight = true;
    });
    this.$root.$on(events.sidebar.unhighlight(this.id), () => {
      console.log(`${this.id} got unhighlight event`); // todo: these are not received...
      this.highlight = false;
    });
    this.handleHideStageTwo();
  },
  computed: {
    classList() {
      return [
        "nav-link",
        this.highlight ? "highlighted" : "",
        this.linkVariant
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
    }
  },
  data() {
    return {
      show_popup: false,
      highlight: false
    };
  }
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.sidebar-analysis-link {
  font-size: 85%;
}
.highlighted {
  background: $gray-500 !important;
}
</style>
