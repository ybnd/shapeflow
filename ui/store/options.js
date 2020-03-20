import Vue from "vue";
import axios from "axios";
import {
  AnalyzerState as ast,
  init,
  get_schemas,
  list,
  launch,
  get_config,
  set_config,
  analyze
} from "../assets/api";

export const state = () => ({
  options: {
    // arrays of available
    feature: [], // features to compute
    transform: [], // transform implementations
    filter: [] // filter implementations
  }
});
