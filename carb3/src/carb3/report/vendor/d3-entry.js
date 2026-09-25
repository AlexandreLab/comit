// The d3 names the carb3 site report uses, and nothing else. d3-sankey (vendored as
// its own file) reads min, max, sum and linkHorizontal from the same global.
export { extent, max, min, sum } from "d3-array";
export { axisBottom, axisLeft } from "d3-axis";
export { easeCubicInOut } from "d3-ease";
export { format } from "d3-format";
export { interpolateNumber } from "d3-interpolate";
export { scaleBand, scaleLinear } from "d3-scale";
export { pointer, select, selectAll } from "d3-selection";
export { area, linkHorizontal, stack, stackOffsetDiverging, stackOrderNone } from "d3-shape";
import "d3-transition";
