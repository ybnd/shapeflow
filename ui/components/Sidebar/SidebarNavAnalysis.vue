<template>
  <router-link
    tag="li"
    class="nav-item nav-dropdown"
    :to="`/analysis/${id}`">
    <div class="nav-link nav-dropdown-toggle" @click="handleClick" >
      <template v-if="state === 'incomplete'"><i class="fa fa-cog" /></template>
      <template v-else-if="state === 'ready'"><i class="fa fa-check-circle-o" /></template>
      <template v-else-if="state === 'running'"><i class="fa fa-spin fa-spinner" /></template>
      <template v-else-if="state === 'done'"><i class="fa fa-check-circle" /></template>
      <template v-else-if="state === 'canceled'"><i class="fa fa-ban" /></template>
      <template v-else-if="state === 'error'"><i class="fa fa-exclamation" /></template>
      {{name}}
    </div>
    <template v-if="state === 'incomplete'">
      <ul class="nav-dropdown-items">
        <SidebarNavLink name="Configure" icon="icon-equalizer" :url="`/analysis/configure?id=${id}`"/>
        <SidebarNavLink name="Set alignment" icon="icon-frame" :url="`/analysis/align?id=${id}`"/>
        <SidebarNavLink name="Set filters" icon="icon-layers" :url="`/analysis/filter?id=${id}`"/>
        <SidebarNavLink name="Remove" icon="icon-trash" :url="`modal`"/>
      </ul>
    </template>
    <template v-else-if="state === 'ready'">
      <ul class="nav-dropdown-items">
        <SidebarNavLink name="Configure" icon="icon-equalizer" :url="`/analysis/configure?id=${id}`"/>
        <SidebarNavLink name="Set alignment" icon="icon-frame" :url="`/analysis/align?id=${id}`"/>
        <SidebarNavLink name="Set filters" icon="icon-layers" :url="`/analysis/filter?id=${id}`"/>
        <SidebarNavLink name="Run" icon="icon-control-play" :url="`/analysis/${id}/analyze`"/>
        <SidebarNavLink name="Remove" icon="icon-trash" :url="`modal`"/>
      </ul>
    </template>
    <template v-else-if="state === 'running'">
      <b-progress class="progress" height="2px" :value="progress"></b-progress>
      <ul class="nav-dropdown-items">
        <SidebarNavLink name="Monitor" icon="icon-graph" :url="`/analysis/monitor?id=${id}`"/>
        <SidebarNavLink name="Cancel" icon="icon-ban" :url="`modal`"/>
      </ul>
    </template>
    <template v-else-if="state === 'done'">
      <b-progress class="progress" height="2px" :value="progress" variant="success"></b-progress>
      <ul class="nav-dropdown-items">
        <SidebarNavLink name="Configure" icon="icon-equalizer" :url="`/analysis/configure?id=${id}`"/>
        <SidebarNavLink name="Set alignment" icon="icon-frame" :url="`/analysis/align?id=${id}`"/>
        <SidebarNavLink name="Set filters" icon="icon-layers" :url="`/analysis/filter?id=${id}`"/>
        <SidebarNavLink name="Run" icon="icon-control-play" :url="`/api/analyzer/${id}/analyze`"/>
        <SidebarNavLink name="Remove" icon="icon-trash" :url="`modal`"/>
      </ul>
    </template>
    <template v-else-if="state === 'canceled'">
      <b-progress class="progress" height="2px" :value="progress" variant="warning"></b-progress>
      <ul class="nav-dropdown-items">
        <SidebarNavLink name="Configure" icon="icon-equalizer" :url="`/analysis/configure?id=${id}`"/>
        <SidebarNavLink name="Set alignment" icon="icon-frame" :url="`/analysis/align?id=${id}`"/>
        <SidebarNavLink name="Set filters" icon="icon-layers" :url="`/analysis/filter?id=${id}`"/>
        <SidebarNavLink name="Run" icon="icon-control-play" :url="`/analysis/${id}/analyze`"/>
        <SidebarNavLink name="Remove" icon="icon-trash" :url="`modal`"/>
      </ul>
    </template>
    <template v-else-if="state === 'error'">
      <b-progress class="progress" height="2px" :value="progress" variant="danger"></b-progress>
      <ul class="nav-dropdown-items">
        <SidebarNavLink name="Configure" icon="icon-equalizer" :url="`/analysis/configure?id=${id}`"/>
        <SidebarNavLink name="Set alignment" icon="icon-frame" :url="`/analysis/align?id=${id}`"/>
        <SidebarNavLink name="Set filters" icon="icon-layers" :url="`/analysis/${id}/configure`"/>
        <SidebarNavLink name="Run" icon="icon-control-play" :url="`/api/analyzer/${id}/analyze`"/>
        <SidebarNavLink name="Remove" icon="icon-trash" :url="`modal`"/>
      </ul>
    </template>
  </router-link>
</template>

<script>
import SidebarFooter from './SidebarFooter'
import SidebarForm from './SidebarForm'
import SidebarHeader from './SidebarHeader'
import SidebarMinimizer from './SidebarMinimizer'
import SidebarNavDivider from './SidebarNavDivider'
import SidebarNavDropdown from './SidebarNavDropdown'
import SidebarNavAnalysis from './SidebarNavAnalysis'
import SidebarNavLink from './SidebarNavLink'
import SidebarNavTitle from './SidebarNavTitle'
import SidebarNavItem from './SidebarNavItem'
import SidebarNavLabel from './SidebarNavLabel'

export default {
  props: {
    name: {
      type: String,
      default: ''
    },
    id: {
      type: String,
      default: ''
    },
    progress: {
      type: Number,
      default: 0,
    },
    state: {
      type: String,
      enum: ['incomplete', 'ready', 'running', 'done', 'canceled', 'error'],
      default: 'incomplete',
    },
    config: {
      type: Object,
      default: () => {
        return {
          video_path: '',
          design_path: '',
        };
      }
    }
  },
  components: {
    SidebarNavLink
  },
  methods: {
    handleClick (e) {
      e.preventDefault();
      e.target.parentElement.classList.toggle('open')
    }
  }
}
</script>
