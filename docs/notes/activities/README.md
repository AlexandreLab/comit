# Activity operation notes

One document per CaRB3 activity (the `carb3_activity` column of
[`activity_process_duty_profile.csv`](../data/activity_process_duty_profile.csv)), saying how a
real plant of that kind is laid out and run. The duty tables say *how much* heat, cooling and
power each process needs in a year; these notes say *how the plant delivers it*: which units
share a header, how the load moves through the day and the year, what is kept as backup, and
where heat is recovered.

They exist so that a model result can be read against how such a site actually works, and so
that inputs the model does not yet have (a backup rule per process, a peak factor, a heat
recovery route) have a sourced place to come from.

**These are reference notes, not data.** Nothing in `R/` or `carb3/` reads them. A value that a
model should use still has to be entered into the data tables with its own provenance.

## Rules for every note

- **Every factual statement carries a source** in the note's Sources section, cited inline as
  `[KEY]` with a page, table or section. A statement with no source is written as a gap in
  section 9, not as a fact.
- **Typical, not universal.** Say what a typical UK site does, and say when practice varies
  with size or product.
- **Process names are the data's names.** Use the `process_id` values from
  `activity_process_duty_profile.csv`, so a reader can join the note to the data.
- **No em dashes.** Use a spaced en dash, a colon or a full stop.

## Template

Every note has these ten sections, in this order, with these headings. If a section has nothing
to say for an activity, keep the heading and say why in one line.

```markdown
# <Activity name>: how the plant operates

*Last updated: YYYY-MM-DD.* Activity key: `<carb3_activity>`. Related worked example: <link or "none">.

## 1. What the activity is
Products, typical UK site size (output, energy use), number of UK sites where known.

## 2. Processes and their duties
One row per `process_id` in the duty profile: what it is physically, the temperature it
needs, the duty family and carrier the data gives it, and whether the data's band matches
practice.

## 3. Energy plant layout
The central utilities (boilers, CHP, chillers, compressors, dryers' own burners) and how they
connect to the processes: steam header, hot water loops, direct firing. Which units serve
which processes together.

## 4. Operating pattern
Hours per day, days per week, shifts, seasonality, batch versus continuous, cleaning cycles,
start-ups. Give a peak-to-mean ratio where a source has one (feeds λ, §5.6 of the live spec).

## 5. Backup and redundancy
For each process: what happens when its main unit is down, and what backup is normally kept
(for example: boilers sized to carry the load with the CHP out). Say which processes have no
backup because the line simply stops.

## 6. Heat recovery and integration
Where waste heat goes in practice: exhaust air preheat, refrigeration heat recovery,
condensate return, vapour recompression.

## 7. Decarbonisation in practice
Which low-carbon routes sites of this kind have actually installed or studied, and what
limits them (temperature, space, grid connection, backup).

## 8. Reading the model's results
What a modeller needs to know to interpret a run for this activity: where the model's
representation differs from the plant and why.

## 9. Gaps and open questions
What no source settled.

## Sources
`[KEY]` Author or publisher, *title*, year, URL, and the page, table or section used.
```

## Index

| Activity | Note | Status |
|---|---|---|
| Creamery | [creamery.md](creamery.md) | Pilot |
| Food Processing Centre | [food_processing_centre.md](food_processing_centre.md) | Pilot |

The other 53 activities have no note yet.
