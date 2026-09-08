# Train-Optimisation-Problem

A Monte Carlo simulation study of **metro train length and service frequency**, comparing 3-car and 6-car train configurations under different passenger-demand and disruption scenarios.

The goal is to understand whether increasing train frequency or increasing train length gives better overall performance when we consider **passenger waiting time, effective capacity, operational cost, and system robustness**.

---

## Problem

Consider two metro operating strategies:

* **3-car trains every 1.5 minutes**
* **6-car trains every 3 minutes**

Both provide the same nominal capacity of **120 car-equivalents/hour** under ideal conditions.

However, nominal capacity does not capture what happens when passenger arrivals vary, dwell times fluctuate, trains fail, or crowding prevents passengers from boarding.

This project investigates the trade-off between **train length and headway** under these conditions.

---

## What I Simulated

I tested **7 train configurations** across **6 demand and disruption scenarios**.

### Train configurations

| Configuration        | Trains/hour |     Nominal capacity |
| -------------------- | ----------: | -------------------: |
| 3-car / 1.5 min      |          40 |     120 car-equiv/hr |
| 3-car / 2.0 min      |          30 |     120 car-equiv/hr |
| 3-car / 2.5 min      |          24 |     120 car-equiv/hr |
| 6-car / 3.0 min      |          20 |     120 car-equiv/hr |
| 6-car / 2.5 min      |          24 |     144 car-equiv/hr |
| 6-car / 2.0 min      |          30 |     180 car-equiv/hr |
| **6-car / 1.75 min** |      **34** | **204 car-equiv/hr** |

### Demand scenarios

The simulation includes:

1. **Off-peak** — 500 passengers/hour
2. **Normal** — 2,000 passengers/hour
3. **Peak** — 4,000 passengers/hour
4. **Surge** — 6,000 passengers/hour
5. **Disruption** — 5,000 passengers/hour with delays and station bottlenecks
6. **Cascading** — 3,000 passengers/hour with multiple simultaneous failures

The scenarios introduce increasing levels of passenger-demand variability, dwell-time variability, and train failures. Failure probabilities range from **1% to 8%**.

---

## Monte Carlo Simulation

For each configuration and scenario, I ran **100 independent simulation runs**.

This gives:

**7 configurations × 6 scenarios × 100 runs = 4,200 simulations**

Randomness is introduced through factors such as:

* Passenger arrival patterns
* Dwell-time variation
* Train failures
* Acceleration/deceleration effects
* Delay propagation
* Crowding and passengers unable to board
* Multiple failure cascades

The simulation therefore evaluates how each configuration behaves across repeated realizations of the same operating conditions rather than relying on a single deterministic run.

---

## Metrics

The configurations are compared using several metrics:

### Passenger experience

* Average waiting time
* Passengers left behind / unserved demand
* Occupancy

### Operational performance

* Number of train movements
* Delay propagation
* Failure effects

### Overall system performance

The simulation combines:

**Passenger Cost + Operational Cost + Reliability Cost**

where passenger cost includes waiting and unserved passengers, operational cost reflects train movements, and reliability cost accounts for failures and delay propagation.

---

## Key Results

### 6-car / 1.75 min performs best overall

Across the simulated scenarios, **6-car trains at 1.75-minute intervals** produced the lowest aggregate system cost.

| Metric                     | 6-car / 1.75 min |
| -------------------------- | ---------------: |
| Average waiting time       |     **21.7 sec** |
| System cost                |        **3,051** |
| Occupancy                  |          **82%** |
| Trains/hour                |           **34** |
| Cost increase under stress |         **+36%** |

The 3-car / 1.5-minute configuration has the lowest average waiting time at **19.8 seconds**, but it is more sensitive to disruptions and has more unserved passengers.

### Effective capacity matters

The simulation shows why equal nominal capacity does not necessarily mean equal real-world performance.

The 3-car / 1.5-minute and 6-car / 3-minute configurations both provide **120 car-equivalents/hour** nominally, but failures and crowding reduce their effective performance differently.

### Shorter headways are not always better

The 3-car / 1.5-minute configuration requires **40 trains/hour**. A relatively small delay can therefore represent a large fraction of the headway and propagate through the system.

The 6-car / 1.75-minute configuration operates at **34 trains/hour**, providing additional headway while retaining relatively high frequency.

---

## Visualizations

The repository includes visualizations for:

* Waiting time, system cost, occupancy and delay propagation
* Passengers left behind
* Pareto frontier between waiting time and system cost
* Scenario-specific Pareto frontiers
* Robustness under disruption
* 3D cost surfaces

These visualizations are generated from the simulation results and can be used to examine the trade-offs between different operating strategies.

### Requirements

```bash
pip install numpy pandas matplotlib seaborn
```

## Limitations

This is a **simulation study**, not a direct model of a particular metro system.

The results depend on the assumptions used for:

* Passenger demand
* Dwell-time variability
* Failure probabilities
* Train capacity
* Headway constraints
* Crowding behaviour
* Delay propagation

For application to a real metro system, these parameters would need to be replaced with observed operational and passenger-demand data.

---

## Conclusion

The main result of this simulation is that **train length and frequency should be considered together rather than optimized independently**.

Under the scenarios tested here, the **6-car / 1.75-minute configuration** provides the best overall balance between passenger waiting time, effective capacity, operational cost, and robustness.

The broader takeaway is:

> **Nominal capacity alone is not enough to evaluate a metro operating strategy.**

Real-world variability, crowding, failures, and delay propagation can change which configuration performs best.

---

## Status

* **Simulation runs:** 4,200
* **Configurations:** 7
* **Scenarios:** 6
* **Runs per configuration-scenario pair:** 100
* **Confidence level:** 95%
* **Method:** Monte Carlo simulation
* **Last updated:** September 2026
