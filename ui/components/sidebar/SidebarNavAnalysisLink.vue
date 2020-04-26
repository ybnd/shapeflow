<template>
  <div>
    <template v-if="isTwoStage">
      <div
        :id="id"
        @click="handleShowStageTwo"
        :class="classList"
        class="sidebar-analysis-link"
      >
        &ensp;
        <i :class="icon"></i> {{ name }}
        <b-badge v-if="badge && badge.text" :variant="badge.variant">{{
          badge.text
        }}</b-badge>
        <b-popover
          :target="id"
          :show.sync="show_popup"
          @ok="doRequest"
          container="body"
          placement="right"
          boundary="viewport"
        >
          <b-button variant="primary" @click="handleClickStageTwo">
            <i class="fa fa-check" /> {{ name }}
          </b-button>
          <b-button variant="danger" @click="handleHideStageTwo">
            <i class="fa fa-times" />
          </b-button>
        </b-popover>
      </div>
    </template>
    <template v-else-if="isApiLink">
      <div
        :id="id"
        @click="doRequest"
        :class="classList"
        class="sidebar-analysis-link"
      >
        &ensp;
        <i :class="icon"></i> {{ name }}
      </div>
    </template>
    <template v-else>
      <div
        :id="id"
        @click="doNavigate"
        :class="classList"
        class="sidebar-analysis-link"
      >
        &ensp;
        <i :class="icon"></i> {{ name }}
      </div>
    </template>
  </div>
</template>
template

<script>
import axios from "axios";

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
      // id should be set to the url
      this.$router.push(this.id);
    },
    doRequest(rl) {
      this.show_popup = false;
      // id should be set to the url
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
  computed: {
    classList() {
      return ["nav-link", this.linkVariant, ...this.itemClasses];
    },
    linkVariant() {
      return this.variant ? `nav-link-${this.variant}` : "";
    },
    itemClasses() {
      return this.classes ? this.classes.split(" ") : [];
    },
    isApiLink() {
      return this.id.substring(0, 4) === "/api";
    },
    isTwoStage() {
      return this.id.substring(0, 5) === "event";
    }
  },
  data() {
    return {
      show_popup: false
    };
  }
};
</script>

<style>
.sidebar-analysis-link {
  font-size: 85%;
}
</style>
