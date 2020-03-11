<template>
  <div class="fixed-page">
    <div class="analysis-card-container">
      <draggable tag="ul" :list="navItems" class="analysis-card-drag" handle=".handle">
        <template v-for="(item) in navItems">
          <AnalysisCard
            v-bind:key="item.id"
            :name="item.name"
            :id="item.id"
            :progress="item.progress"
            :state="item.state"
            :config="item.config"/>
        </template>
      </draggable>
    </div>
  </div>
</template>

<script>

// https://github.com/SortableJS/Vue.Draggable/blob/master/example/components/handle.vue

import nav from '../layouts/menu'
import draggable from 'vuedraggable'
import CardLine1ChartExample from '~/components/dashboard/CardLine1ChartExample'
import CardLine2ChartExample from '~/components/dashboard/CardLine2ChartExample'
import CardLine3ChartExample from '~/components/dashboard/CardLine3ChartExample'
import CardBarChartExample from '~/components/dashboard/CardBarChartExample'
import MainChartExample from '~/components/dashboard/MainChartExample'
import SocialBoxChartExample from '~/components/dashboard/SocialBoxChartExample'
import CalloutChartExample from '~/components/dashboard/CalloutChartExample'
import Callout from '~/components/'
import AnalysisCard from '../components/dashboard/AnalysisCard';

console.log(nav.items);

export default {
  name: 'dashboard',
  components: {
    AnalysisCard,
    draggable,
  },
  data() {
    return {
      navItems: nav.items,

    }
  },
}
</script>


<style>
  /*@import '../assets/scss/core/_variables';*/
  .fixed-page {
    max-height: 100vh;
    flex-direction: column;
    flex-wrap: nowrap;
    overflow-x: hidden;
    overflow-y: scroll;
    -ms-overflow-style: -ms-autohiding-scrollbar;
    margin-left: -20px;
    margin-right: -30px;
  }
  .analysis-card-container {
    flex: 1;
    flex-flow: ro;
    flex-direction: row;
  }
</style>
