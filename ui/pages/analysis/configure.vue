<template>
  <div class="fixed-page">
    <PageHeader>
      <PageHeaderItem>
        <b-button @click="setSettings">Export</b-button>
      </PageHeaderItem>
      <PageHeaderItem>
        <b-button @click="clearCache">Import</b-button>
      </PageHeaderItem>
    </PageHeader>
    <p>
      In the future, you will be able to change analysis configuration directly
      from here, for now just use the align/filter pages or add a new analysis.
    </p>
    <p>
      You'll be able to set:
    </p>

    <ul>
      <li>Name (defaults to # in database, can't be changed for now)</li>
      <li>
        Description (not available for now)
      </li>
      <li>
        Video / design path
      </li>
      <li>
        Frame interval
      </li>
      <li>
        Features & global feature parameters
      </li>
      <li>
        Transform options (type, matrix, region of interest, flip)
      </li>
      <li>
        Global filter type & filter parameters
      </li>
      <li>
        Design rendering
        <ul>
          <li>DPI (affects precision of feature calculations)</li>
          <li>Smoothing (mask -> binary)</li>
        </ul>
      </li>
      <li>
        Mask configuration (for every mask in the design)
        <ul>
          <li>
            Skip mask during analysis
          </li>
          <li>
            Filter type & mask-specific filter parameters
          </li>
          <li>
            Color to filter
          </li>
          <li>
            Mask-specific feature parameters
          </li>
        </ul>
      </li>
    </ul>
  </div>
</template>

<script>
import PageHeader from "../../components/header/PageHeader";
import PageHeaderItem from "../../components/header/PageHeaderItem";
export default {
  name: "dashboard",
  components: { PageHeader, PageHeaderItem },
  beforeMount() {
    this.initConfig();
  },
  methods: {
    initConfig() {
      if (this.$store.getters["analyzers/getIndex"](this.id) === -1) {
        this.$router.push(`/`);
      } else {
      }
    }
  },
  computed: {
    id() {
      return this.$route.query.id;
    }
  },
  data: function() {
    return {};
  }
};
</script>

<style></style>
