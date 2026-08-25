# The journey of one premise

Generated from [the implementation specification](../2026-08-19-carb3-site-decarbonisation-implementation.md) by `docs/notes/examples/build_spec_flow_diagram.py`. Do not edit by hand — regenerate.

What happens to a single premise between arriving from the stock model and leaving as a pathway. 9 steps, in the order §4 specifies them. Data stores are grouped into four lanes by who owns them — the entity name travels on the arrow, so nothing is lost. Solid arrows into a step are reads; dashed arrows out are writes.

```mermaid
sequenceDiagram
    autonumber
    participant Stock as CaRB3 stock model
    participant Ref as Reference data
    participant Scen as Scenario data
    participant Out as Results
    participant A1 as A1 Ingest and validate premise records
    participant A2 as A2 Expand premise to its process set
    participant A3 as A3 Allocate premise energy across processes
    participant A4 as A4 Back-solve implied existing capacity
    participant A5 as A5 Apply the infrastructure scenario
    participant A6 as A6 Build the per-premise optimisation problem
    participant A7 as A7 Solve and extract
    participant A8 as A8 Assemble output tables
    participant A9 as A9 Aggregate to GB and compare
    activate A1
    Stock->>A1: premise_record
    Stock->>A1: premise_energy
    Stock->>A1: premise_throughput
    Ref->>A1: activity_process_register
    A1->>A2: hand off
    deactivate A1
    activate A2
    Ref->>A2: activity_process_register
    Stock->>A2: premise_process_detail
    A2->>A3: hand off
    deactivate A2
    activate A3
    Stock->>A3: premise_energy
    Ref->>A3: activity_process_energy_profile
    Ref->>A3: technology
    A3->>A4: hand off
    deactivate A3
    activate A4
    Ref->>A4: commodity
    Ref->>A4: technology
    Ref->>A4: technology_input_output
    Stock->>A4: premise_process_detail
    Stock->>A4: premise_operating_profile
    A4->>A5: hand off
    deactivate A4
    activate A5
    Scen->>A5: infrastructure_scenario
    A5->>A6: hand off
    deactivate A5
    activate A6
    Ref->>A6: technology
    Scen->>A6: scenario_parameters
    A6->>A7: hand off
    deactivate A6
    activate A7
    Ref->>A7: technology
    A7->>A8: hand off
    deactivate A7
    activate A8
    Ref->>A8: commodity
    Ref->>A8: technology
    A8-->>Out: site_pathway
    A8->>A9: hand off
    deactivate A8
    activate A9
    Stock->>A9: premise_record
    Stock->>A9: premise_energy
    Stock->>A9: premise_connection
    Ref->>A9: activity_process_register
    Ref->>A9: activity_process_energy_profile
    Ref->>A9: commodity
    Ref->>A9: technology
    Ref->>A9: technology_input_output
    Scen->>A9: infrastructure_scenario
    Scen->>A9: scenario_parameters
    Out->>A9: site_pathway
    Stock->>A9: premise_process_detail
    Stock->>A9: premise_measured_emissions
    Stock->>A9: premise_operating_profile
    deactivate A9
```
