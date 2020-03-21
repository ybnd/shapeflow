<template>
  <b-card show-footer class="analysis-card">
    <basic-config
      :ref="form_ref"
      :formStyle="{ width: '300px', direction: 'rtl' }"
      v-bind:config="this.$store.state.analyzers.analyzers[id].config"
    />
    <div slot="footer" class="handle">
      <b-input-group>
        <b-input-group-prepend>
          <b-button
            >#{{ this.$store.getters["queue/getIndex"](id) + 1 }}</b-button
          >
        </b-input-group-prepend>
        <b-form-input
          id="name"
          type="text"
          v-bind:value="this.$store.state.analyzers.analyzers[id].name"
          class="card-name-form"
        ></b-form-input>
      </b-input-group>
    </div>
  </b-card>
</template>

<script>
import { mapGetters, mapState, mapActions } from "vuex";
import BasicConfig from "../config/BasicConfig";

export default {
  props: {
    id: {
      type: String,
      required: true
    }
  },
  components: { BasicConfig },
  methods: {
    ...mapGetters({
      name: "analyzers/getName",
      state: "analyzers/getState",
      config: "analyzers/getConfig",
      index: "analyzers/getIndex"
    })
  },
  computed: {
    form_ref() {
      return this.id + "-form";
    }
  },
  data() {
    return {
      show: false,
      selected: "dt", // todo: this means that the default value is always reset; we should go by the history though!
      interval_placeholder: {
        Nf: "# frames", // todo: this works when `selected`is changed here, but I'm not sure how to make it resolve on click...
        dt: "interval (s)"
      }
    };
  }
};
</script>

<style scoped>
.analysis-card {
  /*text-align: left;*/
  max-width: 800px;
  max-height: 400px;
  min-height: 160px;
  display: flex !important;
  flex-direction: column !important;
  flex-wrap: wrap !important;
  margin: 5px 5px 0 0;
}
.card-name-form {
  margin-left: -3px;
  max-width: 160px;
}
.handle {
  margin-left: -16px;
  margin-top: -8px;
  height: 26px;
}
.thumbnail {
  min-height: 60px;
  min-width: 100px;
  max-height: 100px;
  max-width: 178px;
}
</style>
