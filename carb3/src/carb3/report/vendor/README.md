# Vendored JavaScript for the site report

Inlined into every `site_report.html` so the page renders with the network off. Nothing
here is fetched at run time.

| File | What | Version | Licence |
|---|---|---|---|
| `d3.min.js` | A d3 bundle holding only the names in `d3-entry.js`, as the global `d3` | d3-array 3.2.4, d3-axis 3.0.0, d3-ease 3.0.1, d3-format 3.1.2, d3-interpolate 3.0.1, d3-scale 4.0.2, d3-selection 3.0.0, d3-shape 3.2.0, d3-transition 3.0.1 and their dependencies | ISC; d3-ease also BSD-3-Clause. `LICENSE-d3.txt` |
| `d3-sankey.min.js` | `dist/d3-sankey.min.js` from the npm package, unmodified | d3-sankey 0.12.3 | BSD-3-Clause. `LICENSE-d3-sankey.txt` |

d3-sankey is loaded second and adds `d3.sankey` to the same global, reading `min`, `max`,
`sum` and `linkHorizontal` from it. Removing any of those from `d3-entry.js` breaks it.

## Rebuilding `d3.min.js`

Needs Node and network access. Adding a d3 name the page uses means adding it to
`d3-entry.js` and running this again.

```
mkdir /tmp/d3build && cd /tmp/d3build && npm init -y
npm i d3-array@3.2.4 d3-axis@3.0.0 d3-ease@3.0.1 d3-format@3.1.2 d3-interpolate@3.0.1 \
      d3-scale@4.0.2 d3-selection@3.0.0 d3-shape@3.2.0 d3-transition@3.0.1 \
      d3-sankey@0.12.3 esbuild@0.28.2
cp <repo>/carb3/src/carb3/report/vendor/d3-entry.js .
npx esbuild d3-entry.js --bundle --minify --format=iife --global-name=d3 \
    --legal-comments=none --outfile=<repo>/carb3/src/carb3/report/vendor/d3.min.js
cp node_modules/d3-sankey/dist/d3-sankey.min.js <repo>/carb3/src/carb3/report/vendor/
```
