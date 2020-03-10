<template>
  <router-link tag="li" class="nav-item nav-dropdown" :to="url" disabled>
    <div class="nav-link nav-dropdown-toggle" @click="handleClick"> {{name}} </div>
    <b-progress class="progress" height="2px" :value="progress"></b-progress>
    <ul class="nav-dropdown-items">
      <slot></slot>
    </ul>
  </router-link>
</template>

<script>
export default {
  props: {
    name: {
      type: String,
      default: ''
    },
    url: {
      type: String,
      default: ''
    },
    icon: {
      type: String,
      default: ''
    },
    progress: {
      type: Number,
      default: 0,
    },
    state: {
      type: String,
      enum: [''],
    },
  },
  methods: {
    handleClick (e) {
      e.preventDefault();
      e.target.parentElement.classList.toggle('open')
    }
  }
}
</script>
