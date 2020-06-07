<template>
  <div
    class="result-container"
    :class="container_class"
    ref="container"
    :key="charts_key"
  >
    <template v-for="(feature_data, feature, index) in result">
      <div
        class="result"
        :class="result_class"
        :key="`result-${name}-${feature}`"
      >
        <ResultChart
          :chart-data="{
            datasets: feature_data,
            unit: $store.state.schemas.feature.units[feature],
          }"
          :options="{
            ...options,
            legend: {
              display: is_last(index),
              position: 'bottom',
            },
            scales: {
              xAxes: [
                {
                  scaleLabel: {
                    display: is_last(index),
                    labelString: 'Time (s)',
                    fontStyle: 'bold',
                    fontSize: 14,
                  },
                },
              ],
              yAxes: [
                {
                  scaleLabel: {
                    display: true,
                    labelString: `${$store.state.schemas.feature.labels[feature]} (${$store.state.schemas.feature.units[feature]})`,
                    fontStyle: 'bold',
                    fontSize: 14,
                  },
                },
              ],
            },
          }"
        />
      </div>
    </template>
  </div>
</template>

<script>
import ResultChart from "../../components/results/ResultChart";
import { events } from "../../static/events";

export default {
  name: "ResultChartStack",
  props: {
    container_class: {
      type: String,
      default: "",
    },
    result_class: {
      type: String,
      default: "",
    },
    canvas_class: {
      type: String,
      default: "",
    },
  },
  components: { ResultChart },
  beforeMount() {
    this.updateChartsKey();
    window.onresize = this.updateChartsKey;
    this.$root.$on(events.data.update(this.id), this.updateChartsKey);
  },
  beforeDestroy() {},
  methods: {
    is_last(index) {
      return index === Object.keys(this.result).length - 1;
    },
    updateChartsKey() {
      this.charts_key = Date.now();
    },
  },
  computed: {
    id() {
      return this.$route.query.id;
    },
    name() {
      return this.$store.getters["analyzers/getName"](this.id);
    },
    result() {
      return this.$store.getters["analyzers/getResult"](this.id);
    },
  },
  data() {
    return {
      options: {
        responsive: true,
        maintainAspectRatio: false,
      },
      charts_key: "",
    };
  },
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.result-container {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: 8px;
}
.result {
  position: relative;
  flex-shrink: 1;
  display: flex;
}
</style>
