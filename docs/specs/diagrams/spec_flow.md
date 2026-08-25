# CaRB3 per-site model — data flow

Generated from [the implementation specification](../2026-08-19-carb3-site-decarbonisation-implementation.md) by `docs/notes/examples/build_spec_flow_diagram.py`. Do not edit by hand — regenerate.

15 entities · 9 algorithms · 44 edges. Cylinders are data, boxes are algorithms; dashed edges are reads, solid are writes and the pipeline order. Colour marks who owns the data — see [the README](README.md).

```mermaid
flowchart LR
    premise_record[(premise_record)]
    premise_energy[(premise_energy)]
    premise_throughput[(premise_throughput)]
    premise_connection[(premise_connection)]
    activity_process_register[(activity_process_register)]
    activity_process_energy_profile[(activity_process_energy_profile)]
    commodity[(commodity)]
    technology[(technology)]
    technology_input_output[(technology_input_output)]
    infrastructure_scenario[(infrastructure_scenario)]
    scenario_parameters[(scenario_parameters)]
    site_pathway[(site_pathway)]
    premise_process_detail[(premise_process_detail)]
    premise_measured_emissions[(premise_measured_emissions)]
    premise_operating_profile[(premise_operating_profile)]
    A1["A1 Ingest and validate premise records"]
    A2["A2 Expand premise to its process set"]
    A3["A3 Allocate premise energy across processes"]
    A4["A4 Back-solve implied existing capacity"]
    A5["A5 Apply the infrastructure scenario"]
    A6["A6 Build the per-premise optimisation problem"]
    A7["A7 Solve and extract"]
    A8["A8 Assemble output tables"]
    A9["A9 Aggregate to GB and compare"]
    premise_record --> A1
    premise_energy --> A1
    premise_throughput --> A1
    activity_process_register --> A1
    activity_process_register --> A2
    premise_process_detail --> A2
    premise_energy --> A3
    activity_process_energy_profile --> A3
    technology --> A3
    commodity --> A4
    A4 --> technology
    technology --> A4
    technology_input_output --> A4
    premise_process_detail --> A4
    premise_operating_profile --> A4
    infrastructure_scenario --> A5
    technology --> A6
    scenario_parameters --> A6
    technology --> A7
    commodity --> A8
    technology --> A8
    A8 --> site_pathway
    premise_record --> A9
    premise_energy --> A9
    premise_connection --> A9
    activity_process_register --> A9
    activity_process_energy_profile --> A9
    commodity --> A9
    technology --> A9
    technology_input_output --> A9
    infrastructure_scenario --> A9
    scenario_parameters --> A9
    site_pathway --> A9
    premise_process_detail --> A9
    premise_measured_emissions --> A9
    premise_operating_profile --> A9
    A1 ==> A2
    A2 ==> A3
    A3 ==> A4
    A4 ==> A5
    A5 ==> A6
    A6 ==> A7
    A7 ==> A8
    A8 ==> A9

    classDef input fill:#dbeafe,stroke:#1e40af,stroke-width:2px,color:#0f172a;
    classDef reference fill:#ede9fe,stroke:#5b21b6,stroke-width:2px,color:#0f172a;
    classDef scenario fill:#fef3c7,stroke:#92400e,stroke-width:2px,color:#0f172a;
    classDef output fill:#dcfce7,stroke:#166534,stroke-width:2px,color:#0f172a;
    classDef algorithm fill:#f1f5f9,stroke:#334155,stroke-width:2px,color:#0f172a;
    class premise_record,premise_energy,premise_throughput,premise_connection,premise_process_detail,premise_measured_emissions,premise_operating_profile input;
    class activity_process_register,activity_process_energy_profile,commodity,technology,technology_input_output reference;
    class infrastructure_scenario,scenario_parameters scenario;
    class site_pathway output;
    class A1,A2,A3,A4,A5,A6,A7,A8,A9 algorithm;
```
