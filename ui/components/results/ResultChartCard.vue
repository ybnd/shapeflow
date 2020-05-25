<template>
  <b-card class="result-card" :header="name">
    <div class="result-container">
      <template v-for="(data, feature) in result">
        <div
          class="result"
          :key="`result-${name}-${feature}`"
          @click="handleClick"
        >
          <ResultChart
            :chart-data="{ datasets: feature_data }"
            :options="{ ...options, title: { display: true, text: feature } }"
          />
        </div>
      </template>
    </div>
  </b-card>
</template>

<script>
import ResultChart from "./ResultChart";

export default {
  name: "ResultChartCard",
  components: { ResultChart },
  props: {
    id: {
      type: String,
      required: true
    }
  },
  methods: {
    handleClick() {
      console.log(
        "CLICKED RESULT CARD, SHOULD NAVIGATE TO CORRESPONDING RESULT PAGE"
      );
    }
  },
  computed: {
    name() {
      return this.$store.getters["analyzers/getName"](this.id);
    },
    result() {
      return this.$store.getters["analyzers/getResult"](this.id);
    }
  },
  data() {
    return {
      options: {
        tooltips: {
          enabled: false
        }
      }
    };
  }
};
</script>

<style scoped lang="scss">
.result-card {
}
.result-container {
}
</style>
