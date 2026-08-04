# COMIT Headless Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the COMIT R model callable without Excel or Shiny — a pure `run_comit()` entry point, a format-neutral (parquet) input/output contract with validation, a CLI, and a Docker container — so Python models and cloud pipelines can drive it.

**Architecture:** COMIT is an R package (golem Shiny app) whose core already operates on plain data frames: `read_excel_data_template()` parses the input workbook into a named list of tibbles, `comit_solver()` optimises, `create_tables()` produces output tables, and only then does openxlsx serialise to a workbook. This plan peels the Shiny/Excel layers off those boundaries: extract a pure run function the Shiny app delegates to, add parquet read/write adapters plus schema validation around the same list-of-tables contract, wrap it in a CLI, and containerise. The Excel and Shiny workflows keep working unchanged on top of the new core.

**Tech Stack:** R (≥ 4.x), testthat, nanoparquet (lightweight parquet I/O — no Arrow C++ dependency), jsonlite (run manifest), Docker (rocker/r-ver), renv (dependency pinning).

---

## Context for a developer new to this codebase

- **Package layout:** standard R package. All source in `R/`, tests in `tests/testthat/`, packaged data in `inst/`. The package name is `comit`. The Shiny app is built with golem; files prefixed `mod_` are Shiny modules, `fct_` are plain functions.
- **The input contract today:** `read_excel_data_template(path)` in [R/fct_read_data.R](../../R/fct_read_data.R) returns a named list of data frames — one per workbook sheet (e.g. `Technologies`, `NAEI`, `traded_share`), plus `model_parameters`, a **one-row wide data frame** built by pivoting the `model_parameters_a/b/c` sheets. This list is the real data contract; the workbook is just its human-friendly serialisation.
- **The run loop today:** `run_model_for_all_inputs()` in [R/fct_run_model_for_all_inputs.R](../../R/fct_run_model_for_all_inputs.R) iterates scenarios, calls `comit_solver(raw_data, in_app = TRUE)` (or `comit_counterfactual_solver`), checks the solution with `solved_check()`, builds tables with `create_tables()`, and writes a workbook with `create_output_xlsx()`. It is entangled with Shiny: `app_text_update()`, `progress_updater()`, `shinyjs::html()` in its message handler.
- **`in_app` flag:** many core functions take `in_app`; when `FALSE`, progress-bar calls no-op (see `progress_updater()` in [R/fct_utilities.R](../../R/fct_utilities.R)). Some dev helpers (e.g. `standard_data_read()` in [R/comit_solver.R](../../R/comit_solver.R)) set a **global** `in_app` — be alert for functions that read the global instead of taking the parameter.
- **Reference input workbook:** `data_template_archive/comit_input_1_4_0_public_updated.xlsx` — the **only** workbook in the repo. Beware: `standard_data_read()` in [R/comit_solver.R](../../R/comit_solver.R) (line ~381) still points at the old name `comit_input_1_4_0_public.xlsx`, which no longer exists, so the test suite cannot currently build its fixtures. Task 0 fixes this before anything else.
- **Running tests:** `Rscript -e 'devtools::test(filter = "<pattern>")'` from the repo root. Note `tests/testthat/setup.R` reads the reference workbook and builds solver inputs once per test run — expect ~a minute of setup before any test executes. A **full solve takes several minutes**, so full-pipeline tests are gated behind the `COMIT_RUN_SLOW_TESTS` environment variable.
- **Commit style:** conventional commits (`feat:`, `refactor:`, `test:`, `build:`, `docs:`).

## File structure

| File | Status | Responsibility |
|---|---|---|
| `R/comit_solver.R` | modify | Fix `standard_data_read()` workbook path (Task 0) |
| `R/fct_run_comit.R` | create | Pure headless entry points: `run_comit()`, `run_comit_model()` |
| `R/fct_run_model_for_all_inputs.R` | modify | Shiny loop delegates solving to `run_comit_model()` |
| `R/fct_validate_inputs.R` | create | `validate_inputs()` + schema loader |
| `dev/generate_input_schema.R` | create | Dev script: regenerate `inst/extdata/input_schema.csv` from the reference workbook |
| `inst/extdata/input_schema.csv` | create (generated) | Canonical input schema: table, column, class |
| `R/fct_input_io.R` | create | `write_inputs_dir()` / `read_inputs_dir()` — parquet input adapters |
| `R/fct_output_io.R` | create | `write_outputs_dir()` — parquet output tables + `manifest.json` |
| `inst/cli/run_comit.R` | create | CLI: xlsx-or-parquet in, xlsx-and/or-parquet out |
| `DESCRIPTION` | modify | Add `nanoparquet`, `jsonlite` to Imports |
| `Dockerfile`, `.dockerignore` | create | Containerised batch runner |
| `renv.lock` | create (generated) | Pinned dependency versions |
| `docs/notes/07_integration_guide.md` | create | Contract + orchestration guide for the Python/cloud side |
| `tests/testthat/test-fct_run_comit.R` | create | Tests for Task 1–2 |
| `tests/testthat/test-fct_validate_inputs.R` | create | Tests for Task 3 |
| `tests/testthat/test-fct_input_io.R` | create | Tests for Task 4 |
| `tests/testthat/test-fct_output_io.R` | create | Tests for Task 5 |

**Out of scope (deliberately — YAGNI):** a plumber REST API, cloud-platform-specific orchestration code (Airflow DAGs, ADF pipelines), authentication, any change to the Shiny UI beyond delegating to the new core, replacing Excel for human users.

---

### Task 0: Repair the test fixture path and record the baseline

The whole plan's test strategy depends on `tests/testthat/setup.R` building `raw_data` via `standard_data_read()` — which currently points at a workbook that no longer exists in the repo. Fix that first, and record what the test baseline actually is.

**Files:**
- Modify: `R/comit_solver.R` (`standard_data_read()`, line ~381)

- [ ] **Step 1: Point `standard_data_read()` at the workbook that exists**

In `R/comit_solver.R`, change the filename inside `standard_data_read()`:

```r
      "data_template_archive/comit_input_1_4_0_public.xlsx"
```

becomes

```r
      "data_template_archive/comit_input_1_4_0_public_updated.xlsx"
```

Note: `tests/testthat/setup.R` (line ~46) also assigns a path to a missing `input_template_for_testing.xlsx`, used by `test-fct_read_data.R`. Leave it as is — any resulting failures are pre-existing and get captured in the Step 2 baseline.

- [ ] **Step 2: Verify the test suite can now build its fixtures, and record the baseline**

Run: `Rscript -e 'devtools::test()'`
Expected: setup completes (the reference workbook loads, solver inputs build) and tests execute. Save the pass/fail/skip counts — **this is the baseline** that "no new failures" means in every later task and in the final verification. If any tests fail here, they are pre-existing failures, not caused by this plan; list them in the commit message.

- [ ] **Step 3: Commit**

```bash
git add R/comit_solver.R
git commit -m "fix: point standard_data_read at the workbook present in the repo"
```

---

### Task 1: Pure headless entry point — `run_comit()`

The core deliverable: run the model from a list of input tables, no Shiny, no files.

**Files:**
- Create: `R/fct_run_comit.R`
- Test: `tests/testthat/test-fct_run_comit.R`

- [ ] **Step 1: Write the failing tests**

Create `tests/testthat/test-fct_run_comit.R`:

```r
test_that("run_comit rejects inputs without model_parameters", {
  expect_error(run_comit(list(Technologies = data.frame())),
               regexp = "model_parameters")
})

test_that("run_comit rejects a run with no models enabled", {
  fake_params <- raw_data
  fake_params$model_parameters$run_main <- FALSE
  fake_params$model_parameters$run_counterfactual <- FALSE
  expect_error(run_comit(fake_params), regexp = "Nothing to run")
})

test_that("run_comit_model rejects unknown model names", {
  expect_error(run_comit_model(raw_data, model = "Banana"))
})

test_that("run_comit solves the reference scenario end to end", {
  skip_if(Sys.getenv("COMIT_RUN_SLOW_TESTS") == "",
          "Set COMIT_RUN_SLOW_TESTS=1 to run full-solve tests")

  scenario_data <- raw_data
  scenario_data$model_parameters$run_main <- TRUE
  scenario_data$model_parameters$run_counterfactual <- FALSE

  out <- run_comit(scenario_data)

  expect_named(out, c("results", "meta"))
  expect_named(out$results, "Scenario")
  expect_true(length(out$results$Scenario) > 0)
  expect_true(all(vapply(out$results$Scenario, is.data.frame, logical(1))))
  expect_identical(out$meta$models_run, "Scenario")
})
```

Notes: `raw_data` is created once in `tests/testthat/setup.R` and is visible to all tests. Copying it (`fake_params <- raw_data`) is safe — R copies on modify.

- [ ] **Step 2: Run tests to verify they fail**

Run: `Rscript -e 'devtools::test(filter = "fct_run_comit")'`
Expected: FAIL — `could not find function "run_comit"`.

- [ ] **Step 3: Implement `R/fct_run_comit.R`**

```r
# Headless entry points for running comit without the Shiny app.
# The Shiny run loop (fct_run_model_for_all_inputs.R) delegates to these.

#' Solve one comit model headlessly
#'
#' Runs a single model (Scenario or Counterfactual) from an already-read
#' input list, with no Shiny side effects, and returns the output tables.
#'
#' @param raw_data named list of input tables as produced by
#'  `read_excel_data_template()` or `read_inputs_dir()`.
#' @param model character, either 'Scenario' or 'Counterfactual'.
#' @param in_app boolean, TRUE only when called from the Shiny app so that
#'  progress bars update. Defaults to FALSE for headless use.
#'
#' @return named list of output tables (data frames), as produced by
#'  `create_tables()`.
#' @export
run_comit_model <- function(raw_data,
                            model = c('Scenario', 'Counterfactual'),
                            in_app = FALSE) {

  model <- match.arg(model)

  solved <- if (model == 'Scenario') {
    comit_solver(raw_data, in_app = in_app)
  } else {
    comit_counterfactual_solver(raw_data)
  }

  solved_check(solved)

  tables <- create_tables(solved, raw_data, in_app = in_app)

  gc()

  return(tables)
}


#' Run comit headlessly for one scenario input
#'
#' Pure programmatic entry point: takes the input list, runs whichever of the
#' Scenario/Counterfactual models are enabled in `model_parameters`, and
#' returns all output tables plus run metadata. No Shiny, no file I/O.
#'
#' @inheritParams run_comit_model
#' @param comit_package_version character, recorded in the run metadata.
#'
#' @return list with two elements:
#'  * `results`: named list keyed by model name ('Scenario' and/or
#'    'Counterfactual'), each a named list of output tables.
#'  * `meta`: list with `package_version` and `models_run`.
#' @export
run_comit <- function(raw_data,
                      comit_package_version = get_comit_version()) {

  if (!is.list(raw_data) || is.null(raw_data$model_parameters)) {
    stop("raw_data must be the input list produced by ",
         "read_excel_data_template() or read_inputs_dir(); ",
         "'model_parameters' is missing.", call. = FALSE)
  }

  models_to_run <- c('Scenario', 'Counterfactual')
  models_to_run <- models_to_run[c(isTRUE(raw_data$model_parameters$run_main),
                                   isTRUE(raw_data$model_parameters$run_counterfactual))]

  if (length(models_to_run) == 0) {
    stop("Nothing to run: both run_main and run_counterfactual are FALSE ",
         "in model_parameters.", call. = FALSE)
  }

  results <- list()
  for (model in models_to_run) {
    message("Running model: ", model)
    results[[model]] <- run_comit_model(raw_data, model, in_app = FALSE)
  }

  return(list(results = results,
              meta = list(package_version = comit_package_version,
                          models_run = models_to_run)))
}
```

- [ ] **Step 4: Run the fast tests, verify they pass**

Run: `Rscript -e 'devtools::test(filter = "fct_run_comit")'`
Expected: PASS for the three fast tests; the end-to-end test reports SKIP.

- [ ] **Step 5: Run the slow end-to-end test once**

Run: `COMIT_RUN_SLOW_TESTS=1 Rscript -e 'devtools::test(filter = "fct_run_comit")'`
Expected: PASS (takes several minutes — the solver runs for real). If it fails inside `comit_solver` with an object-not-found error mentioning `in_app`, a core function is reading the global `in_app` instead of its parameter — find it with `grep -n "in_app" R/*.R`, add `in_app` as a parameter with default `FALSE`, and re-run.

- [ ] **Step 6: Regenerate package docs and commit**

```bash
Rscript -e 'devtools::document()'
git add R/fct_run_comit.R tests/testthat/test-fct_run_comit.R NAMESPACE man/
git commit -m "feat: add headless run_comit() entry point"
```

---

### Task 2: Shiny loop delegates to the headless core

Remove the duplicated solve logic so the app and the CLI run the exact same code (DRY).

**Files:**
- Modify: `R/fct_run_model_for_all_inputs.R` (the solve block inside the per-model loop, roughly lines 47–70)

- [ ] **Step 1: Replace the solve/check/tables block**

In `run_model_for_all_inputs()`, the inner `for(model in models_to_run)` loop currently does:

```r
        # get solution and other info
        message("Getting least cost")

        if(model == 'Scenario') {

          solved <- comit_solver(raw_data, in_app = TRUE)

        } else {

          solved <- comit_counterfactual_solver(raw_data)

        }

        gc()

        # See if solver managed to solve
        solved_check(solved)

        tables <- create_tables(solved, raw_data)
```

Replace that whole block with:

```r
        # get solution and other info
        message("Getting least cost")

        tables <- run_comit_model(raw_data, model, in_app = TRUE)
```

Leave everything else in the function untouched (progress updates, `create_output_xlsx`, workbook saving, logging).

- [ ] **Step 2: Run the full test suite**

Run: `Rscript -e 'devtools::test()'`
Expected: same pass/fail profile as the baseline recorded in Task 0 Step 2. No new failures.

- [ ] **Step 3: Manual smoke test of the Shiny app**

Run: `Rscript dev/run_dev.R`, upload `data_template_archive/comit_input_1_4_0_public_updated.xlsx`, run a model, confirm the progress bar advances and an output workbook downloads.

- [ ] **Step 4: Commit**

```bash
git add R/fct_run_model_for_all_inputs.R
git commit -m "refactor: delegate Shiny run loop to run_comit_model()"
```

---

### Task 3: Input schema and validation

Automated pipelines get loud, named errors instead of a cryptic solver crash three minutes in.

**Files:**
- Create: `dev/generate_input_schema.R`
- Create: `inst/extdata/input_schema.csv` (generated)
- Create: `R/fct_validate_inputs.R`
- Test: `tests/testthat/test-fct_validate_inputs.R`

- [ ] **Step 1: Write the schema generator dev script**

Create `dev/generate_input_schema.R`:

```r
# Regenerates inst/extdata/input_schema.csv from the reference input workbook.
# Run from the repo root whenever the input template changes:
#   Rscript dev/generate_input_schema.R

pkgload::load_all('.')

data <- read_excel_data_template(
  'data_template_archive/comit_input_1_4_0_public_updated.xlsx')

schema <- purrr::map_dfr(names(data), function(tbl) {
  df <- data[[tbl]]
  data.frame(table = tbl,
             column = names(df),
             class = vapply(df, function(x) class(x)[1], character(1)))
})

readr::write_csv(schema, 'inst/extdata/input_schema.csv')
message('Wrote ', nrow(schema), ' schema rows for ',
        length(unique(schema$table)), ' tables.')
```

- [ ] **Step 2: Generate the schema file**

Run: `Rscript dev/generate_input_schema.R`
Expected: `Wrote <N> schema rows for <M> tables.` and a new `inst/extdata/input_schema.csv`. Open it and sanity-check a few rows (e.g. `Technologies` rows listing its column names).

- [ ] **Step 3: Write the failing tests**

Create `tests/testthat/test-fct_validate_inputs.R`:

```r
test_that("the reference workbook inputs pass validation", {
  expect_invisible(validate_inputs(raw_data))
})

test_that("a missing table is reported by name", {
  broken <- raw_data
  broken$Technologies <- NULL
  expect_error(validate_inputs(broken), regexp = "Technologies")
})

test_that("a missing column is reported with its table", {
  broken <- raw_data
  broken$Technologies$lifetime <- NULL
  expect_error(validate_inputs(broken), regexp = "Technologies.*lifetime")
})
```

- [ ] **Step 4: Run tests to verify they fail**

Run: `Rscript -e 'devtools::test(filter = "fct_validate_inputs")'`
Expected: FAIL — `could not find function "validate_inputs"`.

- [ ] **Step 5: Implement `R/fct_validate_inputs.R`**

```r
# Validation of the comit input contract (the named list of input tables).
# The canonical schema lives in inst/extdata/input_schema.csv and is
# regenerated from the reference workbook by dev/generate_input_schema.R.

#' Read the canonical input schema shipped with the package
#'
#' @return data frame with columns: table, column, class.
read_input_schema <- function() {
  path <- system.file('extdata', 'input_schema.csv', package = 'comit')
  readr::read_csv(path, show_col_types = FALSE)
}


#' Validate a comit input list against the canonical schema
#'
#' Checks that every expected input table is present and that each table has
#' every expected column. Errors list all problems at once, so a pipeline
#' failure names everything that needs fixing in one pass. Column class
#' mismatches are reported as warnings, not errors, because benign
#' integer/double differences are common across serialisation formats.
#'
#' @param data named list of input tables as produced by
#'  `read_excel_data_template()` or `read_inputs_dir()`.
#' @param schema data frame with columns table/column/class; defaults to the
#'  schema shipped in `inst/extdata/input_schema.csv`.
#'
#' @return invisibly TRUE if valid, otherwise an error listing every problem.
#' @export
validate_inputs <- function(data, schema = read_input_schema()) {

  problems <- character()

  expected_tables <- unique(schema$table)
  missing_tables <- setdiff(expected_tables, names(data))
  if (length(missing_tables) > 0) {
    problems <- c(problems, paste0(
      "Missing input tables: ", paste(missing_tables, collapse = ', ')))
  }

  for (tbl in intersect(expected_tables, names(data))) {

    expected_cols <- schema$column[schema$table == tbl]
    missing_cols <- setdiff(expected_cols, names(data[[tbl]]))

    if (length(missing_cols) > 0) {
      problems <- c(problems, paste0(
        "Table '", tbl, "' is missing columns: ",
        paste(missing_cols, collapse = ', ')))
    }

    table_schema <- schema[schema$table == tbl, ]
    present <- intersect(expected_cols, names(data[[tbl]]))
    actual_classes <- vapply(data[[tbl]][present],
                             function(x) class(x)[1], character(1))
    expected_classes <- table_schema$class[match(present, table_schema$column)]
    mismatched <- present[actual_classes != expected_classes]
    if (length(mismatched) > 0) {
      warning("Table '", tbl, "' has unexpected column classes: ",
              paste(mismatched, collapse = ', '), call. = FALSE)
    }
  }

  if (length(problems) > 0) {
    stop("Invalid comit inputs:\n- ",
         paste(problems, collapse = '\n- '), call. = FALSE)
  }

  invisible(TRUE)
}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `Rscript -e 'devtools::test(filter = "fct_validate_inputs")'`
Expected: PASS. If the first test fails because the schema names tables the reference read doesn't produce (or class warnings fire), the schema was generated from a different workbook than `setup.R` uses — regenerate from `comit_input_1_4_0_public_updated.xlsx` (the same file `standard_data_read()` reads after Task 0) exactly.

- [ ] **Step 7: Document and commit**

```bash
Rscript -e 'devtools::document()'
git add dev/generate_input_schema.R inst/extdata/input_schema.csv \
        R/fct_validate_inputs.R tests/testthat/test-fct_validate_inputs.R \
        NAMESPACE man/
git commit -m "feat: add input schema and validate_inputs()"
```

---

### Task 4: Format-neutral input adapters (parquet)

Excel becomes one adapter among two; cloud pipelines and Python write parquet directly.

**Files:**
- Modify: `DESCRIPTION` (add `nanoparquet` to Imports)
- Create: `R/fct_input_io.R`
- Test: `tests/testthat/test-fct_input_io.R`

- [ ] **Step 1: Add the dependency**

In `DESCRIPTION`, add `nanoparquet` to `Imports:` and `withr` to `Suggests:` (alphabetical order, comma style matching neighbours) — the new tests use `withr::local_tempdir()` and it must be declared or `devtools::check()` will flag it. Then install: `Rscript -e 'install.packages(c("nanoparquet", "withr"))'`.

Why nanoparquet and not arrow: it is a small pure package with no Arrow C++ system dependency, which keeps the Docker image (Task 7) small and the install fast. Its files are standard parquet — pandas/polars read them natively. If richer types or partitioned datasets are needed later, swap to arrow behind the same two functions.

- [ ] **Step 2: Write the failing round-trip test**

Create `tests/testthat/test-fct_input_io.R`:

```r
test_that("inputs round-trip through a parquet directory", {
  dir <- withr::local_tempdir()

  write_inputs_dir(raw_data, dir)

  expect_true(file.exists(file.path(dir, 'Technologies.parquet')))
  expect_true(file.exists(file.path(dir, 'model_parameters.parquet')))

  reread <- read_inputs_dir(dir)

  expect_setequal(names(reread), names(raw_data))
  for (tbl in names(raw_data)) {
    expect_equal(as.data.frame(reread[[tbl]]),
                 as.data.frame(raw_data[[tbl]]),
                 ignore_attr = TRUE)
  }
})

test_that("read_inputs_dir fails clearly on an empty directory", {
  dir <- withr::local_tempdir()
  expect_error(read_inputs_dir(dir), regexp = "No .parquet files")
})
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `Rscript -e 'devtools::test(filter = "fct_input_io")'`
Expected: FAIL — `could not find function "write_inputs_dir"`.

- [ ] **Step 4: Implement `R/fct_input_io.R`**

```r
# Format-neutral input adapters: the same named-list-of-tables contract as
# read_excel_data_template(), serialised as one parquet file per table.

#' Write a comit input list to a directory of parquet files
#'
#' One file per input table, named `<table>.parquet`. Together with
#' `read_inputs_dir()` this makes a parquet directory equivalent to an input
#' workbook, writable from Python/pandas or any cloud pipeline.
#'
#' @param data named list of input tables as produced by
#'  `read_excel_data_template()`.
#' @param dir directory to write to; created if it does not exist.
#'
#' @return invisibly, the directory path.
#' @export
write_inputs_dir <- function(data, dir) {

  dir.create(dir, recursive = TRUE, showWarnings = FALSE)

  for (tbl in names(data)) {
    nanoparquet::write_parquet(as.data.frame(data[[tbl]]),
                               file.path(dir, paste0(tbl, '.parquet')))
  }

  invisible(dir)
}


#' Read a comit input list from a directory of parquet files
#'
#' Inverse of `write_inputs_dir()`. Every `.parquet` file in `dir` becomes an
#' input table named after the file. The result is validated against the
#' canonical schema before being returned.
#'
#' @param dir directory containing one `.parquet` file per input table.
#'
#' @return named list of input tables, same contract as
#'  `read_excel_data_template()`.
#' @export
read_inputs_dir <- function(dir) {

  files <- list.files(dir, pattern = '\\.parquet$', full.names = TRUE)

  if (length(files) == 0) {
    stop("No .parquet files found in ", dir, call. = FALSE)
  }

  data <- lapply(files, function(f) {
    tibble::as_tibble(nanoparquet::read_parquet(f))
  })
  names(data) <- sub('\\.parquet$', '', basename(files))

  validate_inputs(data)

  return(data)
}
```

Note: `tibble::as_tibble()` matters — the solver pipeline was written against tibbles from readxl, and plain data.frame subsetting behaves differently in edge cases. `tibble` is already available via dplyr.

- [ ] **Step 5: Run tests to verify they pass**

Run: `Rscript -e 'devtools::test(filter = "fct_input_io")'`
Expected: PASS. If the round-trip comparison fails on a datetime or list-column, note which table/column in the test output, decide the canonical type (usually: store dates as ISO character), adjust the writer, and re-run.

- [ ] **Step 6: Slow verification — solver accepts parquet-sourced inputs**

Append to `tests/testthat/test-fct_input_io.R`:

```r
test_that("a parquet-sourced input list solves identically", {
  skip_if(Sys.getenv("COMIT_RUN_SLOW_TESTS") == "",
          "Set COMIT_RUN_SLOW_TESTS=1 to run full-solve tests")

  dir <- withr::local_tempdir()
  scenario_data <- raw_data
  scenario_data$model_parameters$run_main <- TRUE
  scenario_data$model_parameters$run_counterfactual <- FALSE

  write_inputs_dir(scenario_data, dir)
  out <- run_comit(read_inputs_dir(dir))

  expect_named(out$results, "Scenario")
})
```

Run: `COMIT_RUN_SLOW_TESTS=1 Rscript -e 'devtools::test(filter = "fct_input_io")'`
Expected: PASS (several minutes).

- [ ] **Step 7: Document and commit**

```bash
Rscript -e 'devtools::document()'
git add DESCRIPTION R/fct_input_io.R tests/testthat/test-fct_input_io.R \
        NAMESPACE man/
git commit -m "feat: add parquet input adapters (write_inputs_dir/read_inputs_dir)"
```

---

### Task 5: Machine-readable outputs — parquet tables + run manifest

Downstream Python models consume tables and run metadata without opening a workbook.

**Files:**
- Modify: `DESCRIPTION` (add `jsonlite` to Imports — check first, shiny already depends on it so it may only need declaring)
- Create: `R/fct_output_io.R`
- Test: `tests/testthat/test-fct_output_io.R`

- [ ] **Step 1: Add `jsonlite` to `DESCRIPTION` Imports**

- [ ] **Step 2: Write the failing test**

Create `tests/testthat/test-fct_output_io.R`. A full solve is slow, so test the writer against a small fake run output that matches `run_comit()`'s return shape:

```r
test_that("write_outputs_dir writes per-model tables and a manifest", {
  dir <- withr::local_tempdir()

  fake_run <- list(
    results = list(
      Scenario = list(
        energy = data.frame(site_ID = c('A', 'B'), value = c(1.5, 2.5)),
        emissions = data.frame(site_ID = c('A', 'B'), value = c(0.1, 0.2))
      )
    ),
    meta = list(package_version = '1.4.0', models_run = 'Scenario')
  )

  write_outputs_dir(fake_run, dir)

  expect_true(file.exists(file.path(dir, 'Scenario', 'energy.parquet')))
  expect_true(file.exists(file.path(dir, 'Scenario', 'emissions.parquet')))

  manifest <- jsonlite::read_json(file.path(dir, 'manifest.json'))
  expect_equal(manifest$package_version, '1.4.0')
  expect_equal(manifest$models_run, 'Scenario')
  expect_setequal(unlist(manifest$tables$Scenario), c('energy', 'emissions'))

  reread <- nanoparquet::read_parquet(file.path(dir, 'Scenario', 'energy.parquet'))
  expect_equal(reread$value, c(1.5, 2.5))
})
```

- [ ] **Step 3: Run test to verify it fails**

Run: `Rscript -e 'devtools::test(filter = "fct_output_io")'`
Expected: FAIL — `could not find function "write_outputs_dir"`.

- [ ] **Step 4: Implement `R/fct_output_io.R`**

```r
# Machine-readable run outputs: one parquet file per output table plus a
# manifest.json describing the run. The xlsx workbook (create_output_xlsx)
# remains the human-facing format; this is the pipeline-facing one.

#' Write comit run output as parquet tables plus a manifest
#'
#' Creates `<dir>/<model>/<table>.parquet` for every output table of every
#' model run, and `<dir>/manifest.json` recording package version, models
#' run, timestamp and the table listing. Non-data-frame tables are skipped
#' with a warning rather than failing the run.
#'
#' @param run_output list as returned by `run_comit()`.
#' @param dir directory to write to; created if it does not exist.
#'
#' @return invisibly, the directory path.
#' @export
write_outputs_dir <- function(run_output, dir) {

  dir.create(dir, recursive = TRUE, showWarnings = FALSE)

  written <- list()

  for (model in names(run_output$results)) {

    model_dir <- file.path(dir, model)
    dir.create(model_dir, showWarnings = FALSE)

    tables <- run_output$results[[model]]

    for (tbl in names(tables)) {
      if (!is.data.frame(tables[[tbl]])) {
        warning("Skipping non-tabular output '", tbl, "' for model ",
                model, call. = FALSE)
        next
      }
      nanoparquet::write_parquet(as.data.frame(tables[[tbl]]),
                                 file.path(model_dir, paste0(tbl, '.parquet')))
      written[[model]] <- c(written[[model]], tbl)
    }
  }

  manifest <- list(
    package_version = run_output$meta$package_version,
    models_run = run_output$meta$models_run,
    written_at_utc = format(Sys.time(), '%Y-%m-%dT%H:%M:%SZ', tz = 'UTC'),
    tables = written
  )

  jsonlite::write_json(manifest,
                       file.path(dir, 'manifest.json'),
                       auto_unbox = TRUE, pretty = TRUE)

  invisible(dir)
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `Rscript -e 'devtools::test(filter = "fct_output_io")'`
Expected: PASS.

- [ ] **Step 6: Check output table names are filesystem-safe**

Real output table names come from `create_output_tables()`. Verify none contain `/` or other characters illegal in filenames:

Run: `grep -n "tables\[\[\|names(tables)\|list(" R/fct_create_output_tables.R | head -30` and inspect how the returned list is named. If any names contain path-hostile characters, sanitise in `write_outputs_dir` (e.g. `gsub('[^A-Za-z0-9_.-]', '_', tbl)`) and record the mapping in the manifest.

- [ ] **Step 7: Document and commit**

```bash
Rscript -e 'devtools::document()'
git add DESCRIPTION R/fct_output_io.R tests/testthat/test-fct_output_io.R \
        NAMESPACE man/
git commit -m "feat: add parquet output writer with run manifest"
```

---

### Task 6: CLI entry point

One command any orchestrator (or `subprocess.run` from Python) can call.

**Files:**
- Create: `inst/cli/run_comit.R`

- [ ] **Step 1: Write the CLI script**

Create `inst/cli/run_comit.R`:

```r
#!/usr/bin/env Rscript

# Headless comit runner.
#
# Usage:
#   Rscript inst/cli/run_comit.R --input <path> --output-dir <dir> [--format xlsx|parquet|both]
#
#   --input       an input .xlsx workbook OR a directory of input .parquet files
#   --output-dir  directory for outputs (created if missing)
#   --format      output format(s); default 'both'
#
# Exit codes: 0 success, 1 bad arguments, 2 model/validation failure.

parse_cli_args <- function(args) {
  parsed <- list(format = 'both')
  i <- 1
  while (i <= length(args)) {
    key <- args[i]
    if (!key %in% c('--input', '--output-dir', '--format')) {
      stop('Unknown argument: ', key, call. = FALSE)
    }
    if (i == length(args)) stop('Missing value for ', key, call. = FALSE)
    parsed[[sub('^--', '', gsub('-', '_', key))]] <- args[i + 1]
    i <- i + 2
  }
  if (is.null(parsed$input) || is.null(parsed$output_dir)) {
    stop('Both --input and --output-dir are required.', call. = FALSE)
  }
  if (!parsed$format %in% c('xlsx', 'parquet', 'both')) {
    stop("--format must be one of: xlsx, parquet, both", call. = FALSE)
  }
  parsed
}

main <- function(args) {

  opts <- tryCatch(parse_cli_args(args), error = function(e) {
    message(conditionMessage(e)); quit(status = 1)
  })

  # Installed package if available (container); source tree otherwise (dev).
  if (!requireNamespace('comit', quietly = TRUE)) {
    pkgload::load_all('.', quiet = TRUE)
  } else {
    library(comit)
  }

  result <- tryCatch({

    raw_data <- if (grepl('\\.xlsx$', opts$input)) {
      read_excel_data_template(opts$input)
    } else {
      read_inputs_dir(opts$input)
    }
    validate_inputs(raw_data)

    run_output <- run_comit(raw_data)

    dir.create(opts$output_dir, recursive = TRUE, showWarnings = FALSE)

    if (opts$format %in% c('parquet', 'both')) {
      write_outputs_dir(run_output, opts$output_dir)
    }

    if (opts$format %in% c('xlsx', 'both')) {
      version <- run_output$meta$package_version
      for (model in names(run_output$results)) {
        wb <- create_output_xlsx(run_output$results[[model]], raw_data, version)
        openxlsx::saveWorkbook(
          wb,
          file.path(opts$output_dir, paste0(model, '_output.xlsx')),
          overwrite = TRUE)
      }
    }

    message('Done. Outputs written to ', opts$output_dir)
    0
  }, error = function(e) {
    message('COMIT run failed: ', conditionMessage(e))
    2
  })

  quit(status = result)
}

main(commandArgs(trailingOnly = TRUE))
```

Note: `create_output_xlsx` and any helpers it needs must be exported (check `NAMESPACE`; if not exported, either export them via `@export` roxygen tags or call with `comit:::` — prefer exporting, they are now part of the public contract).

- [ ] **Step 2: Smoke test both formats end to end**

Run (from repo root; takes several minutes):

```bash
Rscript inst/cli/run_comit.R \
  --input data_template_archive/comit_input_1_4_0_public_updated.xlsx \
  --output-dir /tmp/comit_cli_test --format both
```

Expected: exit 0; `/tmp/comit_cli_test/` contains `manifest.json`, a `Scenario/` (and/or `Counterfactual/`) directory of `.parquet` files, and `Scenario_output.xlsx`. Open the xlsx and spot-check it matches a Shiny-produced output for the same input. One expected difference: CLI workbooks have no `Log` sheet — `add_log_to_wb()` is Shiny-loop-only and deliberately not called here (the manifest plus stderr is the CLI's log).

- [ ] **Step 3: Smoke test the failure path**

Run: `Rscript inst/cli/run_comit.R --input nonexistent.xlsx --output-dir /tmp/x`
Expected: `COMIT run failed: ...` message and exit code 2 (`echo $?`).

- [ ] **Step 4: Commit**

```bash
git add inst/cli/run_comit.R
git commit -m "feat: add CLI runner for headless comit execution"
```

---

### Task 7: Reproducible environment — renv + Docker

**Files:**
- Create: `renv.lock` (generated), `.Rprofile` (generated by renv)
- Create: `Dockerfile`, `.dockerignore`

- [ ] **Step 1: Initialise renv and snapshot**

```bash
Rscript -e 'install.packages("renv"); renv::init(bare = TRUE)'
Rscript -e 'renv::settings$snapshot.type("explicit"); renv::install(); renv::snapshot()'
```

`snapshot.type("explicit")` pins exactly what `DESCRIPTION` declares. Commit `renv.lock`, `.Rprofile`, and `renv/activate.R` (renv prints which files to commit).

- [ ] **Step 2: Write `.dockerignore`**

```
outputs/
renv/library/
renv/staging/
.git/
docs/
*.zip
```

- [ ] **Step 3: Write the Dockerfile**

```dockerfile
FROM rocker/r-ver:4.4.1

# System libraries: sf needs GDAL/GEOS/PROJ/udunits; ROI.plugin.symphony
# needs COIN-OR SYMPHONY; highs needs cmake to build.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgdal-dev libgeos-dev libproj-dev libudunits2-dev \
    libcurl4-openssl-dev libssl-dev libxml2-dev zlib1g-dev \
    coinor-libsymphony-dev coinor-libcgl-dev coinor-libclp-dev \
    cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Restore pinned dependencies first so this layer caches across code changes.
COPY renv.lock renv.lock
RUN Rscript -e "install.packages('renv'); renv::restore()"

# Install the package itself.
COPY . /app
RUN Rscript -e "install.packages('.', repos = NULL, type = 'source')"

ENTRYPOINT ["Rscript", "/app/inst/cli/run_comit.R"]
```

`rocker/r-ver` images default to Posit Package Manager Linux binaries, so `renv::restore()` mostly downloads prebuilt packages. Expect the first build to take a while regardless (sf, highs).

- [ ] **Step 4: Build and smoke test the container**

```bash
docker build -t comit:dev .
mkdir -p /tmp/comit_docker_out
docker run --rm \
  -v "$PWD/data_template_archive:/data:ro" \
  -v /tmp/comit_docker_out:/out \
  comit:dev --input /data/comit_input_1_4_0_public_updated.xlsx \
            --output-dir /out --format parquet
```

Expected: exit 0; `/tmp/comit_docker_out/manifest.json` exists and lists the run's tables. If the build fails compiling a solver package, the missing system library name is in the error tail — add its `-dev` package to the apt-get line and rebuild.

- [ ] **Step 5: Commit**

```bash
git add renv.lock .Rprofile renv/activate.R renv/settings.json Dockerfile .dockerignore
git commit -m "build: add renv lockfile and Docker image for headless runs"
```

---

### Task 8: Integration guide for the Python/cloud side

**Files:**
- Create: `docs/notes/07_integration_guide.md`
- Modify: `docs/notes/README.md` (add index entry, matching the existing list style)

- [ ] **Step 1: Write the guide**

Create `docs/notes/07_integration_guide.md` covering, with this structure:

1. **Ways to run COMIT** — Shiny app (humans), CLI (`Rscript inst/cli/run_comit.R ...`), Docker (`docker run comit:dev ...`), each with a copy-pasteable command.
2. **Input contract** — inputs are a named set of tables (one workbook sheet ⇔ one parquet file), schema defined in `inst/extdata/input_schema.csv`; how to regenerate it; note that `model_parameters` is a single-row table.
3. **Output contract** — `manifest.json` fields, per-model parquet directories, the xlsx as human-facing equivalent.
4. **Calling from Python** — a worked example:

```python
import json
import subprocess
from pathlib import Path

import pandas as pd

out = Path("comit_out")
subprocess.run(
    ["docker", "run", "--rm",
     "-v", f"{Path('inputs').resolve()}:/data:ro",
     "-v", f"{out.resolve()}:/out",
     "comit:dev",
     "--input", "/data",            # directory of .parquet input tables
     "--output-dir", "/out",
     "--format", "parquet"],
    check=True,
)

manifest = json.loads((out / "manifest.json").read_text())
tables = {name: pd.read_parquet(out / "Scenario" / f"{name}.parquet")
          for name in manifest["tables"]["Scenario"]}
```

5. **Orchestration pattern** — the model is a stateless batch job: stage inputs to a working directory (from blob storage or upstream Python models), run the container, collect outputs from the manifest. Works identically under Airflow/Prefect/Dagster or a cloud-native pipeline; exit code 0/2 is the success signal.
6. **What is deliberately not built yet** — REST API (plumber) if on-demand triggering is ever needed; partitioned/arrow datasets if tables outgrow single files.

Verify every table/file name mentioned in the guide against what Task 6's smoke test actually produced — no invented names.

- [ ] **Step 2: Index it and commit**

Add a line for the new note in `docs/notes/README.md`, then:

```bash
git add docs/notes/07_integration_guide.md docs/notes/README.md
git commit -m "docs: add integration guide for headless comit runs"
```

---

## Final verification (whole plan)

- [ ] `Rscript -e 'devtools::test()'` — no new failures vs the baseline recorded in Task 0 Step 2.
- [ ] `COMIT_RUN_SLOW_TESTS=1 Rscript -e 'devtools::test(filter = "fct_run_comit|fct_input_io")'` — full-solve tests pass.
- [ ] `Rscript -e 'devtools::check()'` — no new ERRORs/WARNINGs vs baseline (note the baseline before starting).
- [ ] Docker smoke test (Task 7 Step 4) passes from a clean checkout.
- [ ] Shiny app still runs and produces an output workbook (Task 2 Step 3).
