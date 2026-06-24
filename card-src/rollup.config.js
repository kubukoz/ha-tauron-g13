import resolve from "@rollup/plugin-node-resolve";
import typescript from "@rollup/plugin-typescript";

// Bundle the Lit card + its lit dependency into a single ES module that Home
// Assistant serves as a Lovelace resource. Output is committed into the
// integration (HACS does not run a build on install).
export default {
  input: "src/tauron-g13-timeline.ts",
  output: {
    file: "../custom_components/tauron_g13/frontend/tauron-g13-timeline.js",
    format: "es",
    sourcemap: false,
  },
  plugins: [resolve(), typescript({ tsconfig: "./tsconfig.json" })],
};
