<template>
  <div class="fixed-page">
    <draggable tag="ul" :list="navItems" class="analysis-card-drag" handle=".handle">
      <template v-for="(item, index) in navItems">
        <AnalysisCard
          v-bind:key="item.id"
          :name="item.name"
          :index="index"
          :id="item.id"
          :progress="item.progress"
          :state="item.state"
          :config="item.config"/>
      </template>
    </draggable>
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
.analysis-card-drag {
  flex: 1;
  display: flex !important;
  flex-direction: column !important;
  flex-wrap: wrap !important;
  justify-content: flex-start;
  align-content: flex-start;
  margin-left: -36px;
  margin-right: 6px;
}
</style>
