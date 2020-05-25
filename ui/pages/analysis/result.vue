<template>
  <div class="fixed-page">
    <div class="result-container" ref="container" :key="charts_key">
      <template v-for="(feature_data, feature, index) in result" >
        <div class="result" :key="`result-${name}-${feature}`">
          <ResultChart
            :chart-data="{
              datasets: feature_data,
              unit: $store.state.options.feature.units[feature]
            }"
            :options="{
              ...options,
              legend: {
                display: is_last(index),
                position: 'bottom'
              },
              scales: {
                xAxes: [
                  {
                    scaleLabel: {
                      display: is_last(index),
                      labelString: 'Time (s)',
                      fontStyle: 'bold',
                      fontSize: 14
                    }
                  }
                ],
                yAxes: [
                  {
                    scaleLabel: {
                      display: true,
                      labelString: `${$store.state.options.feature.labels[feature]} (${$store.state.options.feature.units[feature]})`,
                      fontStyle: 'bold',
                      fontSize: 14
                    }
                  }
                ]
              }
            }"
          />
        </div>
      </template>
    </div>
  </div>
</template>

<script>
import ResultChart from "../../components/results/ResultChart";

export default {
  name: "result",
  components: { ResultChart },
  beforeMount() {
    this.updateChartsKey();
    window.onresize = this.updateChartsKey;
  },
  methods: {
    is_last(index) {
      return index === Object.keys(this.result).length - 1;
    },
    updateChartsKey() {
      this.charts_key = Date.now()
    }
  },
  computed: {
    id() {
      return this.$route.query.id;
    },
    name() {
      return this.$store.getters["analyzers/getName"](this.id);
    },
    result() {
      let result = this.$store.getters["analyzers/getResult"](this.id);

      console.log("store state =");
      console.log(this.$store.state);

      console.log("result = ");
      console.log(result);
      return result;
    }
  },
  data() {
    return {
      options: {
        responsive: true,
        maintainAspectRatio: false
      },
      charts_key: ''
    };
  }
};
</script>

<style lang="scss">
@import "../../assets/scss/_bootstrap-variables";
@import "../../assets/scss/_core-variables";
@import "node_modules/bootstrap/scss/functions";

.result-container {
  width: calc(100vw - #{$sidebar-width} -16px);
  height: calc(100vh - 10px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  padding-top: 8px;
}
.result {
  position: relative;
  flex-shrink: 1;
  flex-basis: 100vh;
  max-height: 100vh;
  min-height: 200px;
  display: flex;
  width: calc(100vw - #{$sidebar-width});
  min-width: calc(100vw - #{$sidebar-width});
  max-width: calc(100vw - #{$sidebar-width});
}
.result canvas {
  /*flex-grow: 1;*/
  width: calc(100vw - #{$sidebar-width});
}
</style>
