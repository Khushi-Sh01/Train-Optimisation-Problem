import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from dataclasses import dataclass
from typing import List, Dict, Tuple
import warnings
warnings.filterwarnings('ignore')
np.random.seed(42)

@dataclass
class TrainConfig:
    name: str
    cars: int
    headway_minutes: float
    capacity_per_car: int = 100
    
    @property
    def capacity(self):
        return self.cars * self.capacity_per_car
    
    @property
    def trains_per_hour(self):
        return 60 / self.headway_minutes
    
    @property
    def hourly_capacity(self):
        return self.capacity * self.trains_per_hour


@dataclass
class ScenarioParams:
    """Parameters for a specific scenario"""
    name: str
    demand_passengers_per_hour: float
    dwell_time_mean_sec: float
    dwell_time_std_sec: float
    acceleration_time_sec: float
    passenger_arrival_distribution: str  # 'random', 'clustered', 'uniform'
    failure_probability: float  # Probability train fails (0-1)
    signal_headway_min_sec: float  # Minimum safe headway
    

@dataclass
class SimulationResult:
    """Result from a single simulation run"""
    config_name: str
    scenario_name: str
    avg_waiting_time_sec: float
    max_waiting_time_sec: float
    passengers_served: int
    passengers_left_behind: int
    avg_occupancy_rate: float
    max_occupancy_rate: float
    avg_train_delay_sec: float
    max_train_delay_sec: float
    delay_propagation_count: int
    failed_trains: int
    operational_cost_index: float  # Relative cost
    total_system_cost: float
class MetroSimulation:    
    def __init__(self, config: TrainConfig, scenario: ScenarioParams, 
                 simulation_time_hours: float = 1.0, num_simulations: int = 100):
        self.config = config
        self.scenario = scenario
        self.simulation_time_hours = simulation_time_hours
        self.num_simulations = num_simulations
        
    def generate_passenger_arrivals(self, num_passengers: int) -> np.ndarray:
        total_seconds = self.simulation_time_hours * 3600
        
        if self.scenario.passenger_arrival_distri         
      arrival_times = np.sort(np.random.exponential(
                total_seconds / num_passengers, 
                num_passengers
            ))
        elif self.scenario.passenger_arrival_distribution == 'clustered':
            arrival_times = np.sort(np.random.gamma(
                2, 
                total_seconds / num_passengers, 
                num_passengers
            ))
        else:  # uniform
            arrival_times = np.sort(np.random.uniform(
                0, 
                total_seconds, 
                num_passengers
            ))
        
        return np.clip(arrival_times, 0, total_seconds)
    
    def generate_train_schedule(self) -> np.ndarray:
        """Generate scheduled train departure times"""
        total_seconds = self.simulation_time_hours * 3600
        headway_sec = self.config.headway_minutes * 60
        
        num_trains = int(total_seconds / headway_sec) + 2
        scheduled_times = np.arange(num_trains) * headway_sec
        actual_times = scheduled_times.copy().astype(float)
        delay_std = self.scenario.signal_headway_min_sec / 2
        actual_times += np.random.normal(0, delay_std, len(actual_times))
        actual_times = np.clip(actual_times, 0, total_seconds + headway_sec)
        
        return np.sort(actual_times)
    
    def apply_train_failures(self, train_schedule: np.ndarray) -> Tuple[np.ndarray, List[int]]:
        failed_indices = []
        modified_schedule = train_schedule.copy()
        
        for i, time in enumerate(train_schedule):
            if np.random.random() < self.scenario.failure_probability:
                failed_indices.append(i)
                modified_schedule[i] = -1
        
        return modified_schedule[modified_schedule >= 0], failed_indices
    
    def calculate_dwell_times(self, num_trains: int) -> np.ndarray:
        dwell_times = np.random.normal(
            self.scenario.dwell_time_mean_sec,
            self.scenario.dwell_time_std_sec,
            num_trains
        )
        return np.clip(dwell_times, self.scenario.dwell_time_mean_sec * 0.3, 
                      self.scenario.dwell_time_mean_sec * 3.0)
    
    def simulate_once(self) -> SimulationResult:
        total_seconds = self.simulation_time_hours * 3600
        expected_passengers = int(self.scenario.demand_passengers_per_hour * self.simulation_time_hours)
        passenger_arrivals = self.generate_passenger_arrivals(expected_passengers)
                scheduled_trains = self.generate_train_schedule()
        actual_trains, failed_indices = self.apply_train_failures(scheduled_trains)
        
        dwell_times = self.calculate_dwell_times(len(actual_trains))
        
        waiting_times = []
        passengers_served = 0
        passengers_left_behind = 0
        occupancy_rates = []
        train_delays = []
        max_delay = 0
        delay_propagation = 0
        
        passenger_idx = 0
        
        for train_idx, train_departure in enumerate(actual_trains):
            if train_departure >= total_seconds:
                break
            
            train_capacity = self.config.capacity
            passengers_for_this_train = []
            while (passenger_idx < len(passenger_arrivals) and 
                   passenger_arrivals[passenger_idx] < train_departure + 30):
                if passenger_arrivals[passenger_idx] < total_seconds:
                    passengers_for_this_train.append(passenger_arrivals[passenger_idx])
                passenger_idx += 1
            
            # Simulate boarding
            boarded = 0
            for arrival_time in passengers_for_this_train:
                if boarded < train_capacity:
                    waiting_time = (train_departure - arrival_time)
                    if waiting_time >= 0:
                        waiting_times.append(waiting_time)
                        passengers_served += 1
                        boarded += 1
                else:
                    passengers_left_behind += 1
            
            # Track occupancy
            occupancy_rate = min(1.0, boarded / train_capacity) if train_capacity > 0 else 0
            occupancy_rates.append(occupancy_rate)
            
            # Calculate delay (vs scheduled)
            scheduled_time = scheduled_trains[train_idx + len(failed_indices)] if train_idx < len(scheduled_trains) else scheduled_trains[-1]
            delay = train_departure - scheduled_time
            train_delays.append(max(0, delay))
            
            # Detect delay propagation (delay > 20% of headway = propagated)
            headway_sec = self.config.headway_minutes * 60
            if delay > (0.2 * headway_sec) and train_idx > 0:
                if train_delays[train_idx - 1] > 0:
                    delay_propagation += 1
            
            max_delay = max(max_delay, delay)
        
        # Calculate costs
        operational_cost = len(actual_trains) * (0.1 if self.config.cars == 3 else 0.15)
        operational_cost += len(failed_indices) * 0.5  # Failure penalty
        
        waiting_cost = np.sum(waiting_times) / 60 if waiting_times else 0  # Convert to minutes
        crowding_cost = passengers_left_behind * 2.0  # Heavy penalty for unserved passengers
        delay_cost = np.sum(train_delays) / 60 if train_delays else 0
        
        total_cost = operational_cost + waiting_cost + crowding_cost + delay_cost
        
        return SimulationResult(
            config_name=self.config.name,
            scenario_name=self.scenario.name,
            avg_waiting_time_sec=np.mean(waiting_times) if waiting_times else 0,
            max_waiting_time_sec=np.max(waiting_times) if waiting_times else 0,
            passengers_served=passengers_served,
            passengers_left_behind=passengers_left_behind,
            avg_occupancy_rate=np.mean(occupancy_rates) if occupancy_rates else 0,
            max_occupancy_rate=np.max(occupancy_rates) if occupancy_rates else 0,
            avg_train_delay_sec=np.mean(train_delays) if train_delays else 0,
            max_train_delay_sec=max_delay,
            delay_propagation_count=delay_propagation,
            failed_trains=len(failed_indices),
            operational_cost_index=operational_cost,
            total_system_cost=total_cost
        )
    
    def run(self) -> List[SimulationResult]:
        """Run multiple simulations and return aggregated results"""
        results = []
        for _ in range(self.num_simulations):
            results.append(self.simulate_once())
        return results

def create_scenarios() -> List[ScenarioParams]:
    """Create all test scenarios"""
    scenarios = [
        # OFF-PEAK: Low demand, stable conditions
        ScenarioParams(
            name="OFF-PEAK\n(Low, Stable)",
            demand_passengers_per_hour=500,
            dwell_time_mean_sec=25,
            dwell_time_std_sec=5,
            acceleration_time_sec=15,
            passenger_arrival_distribution='random',
            failure_probability=0.01,
            signal_headway_min_sec=60
        ),
        
        ScenarioParams(
            name="NORMAL\n(Moderate, Typical)",
            demand_passengers_per_hour=2000,
            dwell_time_mean_sec=35,
            dwell_time_std_sec=10,
            acceleration_time_sec=20,
            passenger_arrival_distribution='clustered',
            failure_probability=0.02,
            signal_headway_min_sec=60
        ),
        
        # PEAK: High demand, moderate variation
        ScenarioParams(
            name="PEAK\n(High, Busy)",
            demand_passengers_per_hour=4000,
            dwell_time_mean_sec=40,
            dwell_time_std_sec=15,
            acceleration_time_sec=25,
            passenger_arrival_distribution='clustered',
            failure_probability=0.025,
            signal_headway_min_sec=60
        ),
        
        # SURGE: Very high demand, high variation
        ScenarioParams(
            name="SURGE\n(Very High)",
            demand_passengers_per_hour=6000,
            dwell_time_mean_sec=50,
            dwell_time_std_sec=20,
            acceleration_time_sec=30,
            passenger_arrival_distribution='clustered',
            failure_probability=0.03,
            signal_headway_min_sec=60
        ),
        
        # DISRUPTION: Delayed stations, high variation
        ScenarioParams(
            name="DISRUPTION\n(Delays + Surge)",
            demand_passengers_per_hour=5000,
            dwell_time_mean_sec=60,
            dwell_time_std_sec=30,
            acceleration_time_sec=35,
            passenger_arrival_distribution='clustered',
            failure_probability=0.05,
            signal_headway_min_sec=60
        ),
        
        # CASCADING: Multiple failures
        ScenarioParams(
            name="CASCADING\n(Failures + Delays)",
            demand_passengers_per_hour=3000,
            dwell_time_mean_sec=45,
            dwell_time_std_sec=25,
            acceleration_time_sec=30,
            passenger_arrival_distribution='random',
            failure_probability=0.08,
            signal_headway_min_sec=60
        ),
    ]
    return scenarios


def create_train_configs() -> List[TrainConfig]:
    """Create all train configurations to test"""
    configs = [
        # 3-car configurations
        TrainConfig(name="3-car / 1.5 min", cars=3, headway_minutes=1.5),
        TrainConfig(name="3-car / 2.0 min", cars=3, headway_minutes=2.0),
        TrainConfig(name="3-car / 2.5 min", cars=3, headway_minutes=2.5),
        
        # 6-car configurations
        TrainConfig(name="6-car / 3.0 min", cars=6, headway_minutes=3.0),
        TrainConfig(name="6-car / 2.5 min", cars=6, headway_minutes=2.5),
        TrainConfig(name="6-car / 2.0 min", cars=6, headway_minutes=2.0),
        
        # Aggressive configurations
        TrainConfig(name="6-car / 1.75 min", cars=6, headway_minutes=1.75),
    ]
    return configs
class SimulationAnalysis:
    
    def __init__(self, results: List[SimulationResult]):
        self.results = results
        self.df = pd.DataFrame([vars(r) for r in results])
    
    def create_summary_table(self) -> pd.DataFrame:
        """Create summary statistics by configuration and scenario"""
        summary = self.df.groupby(['config_name', 'scenario_name']).agg({
            'avg_waiting_time_sec': ['mean', 'std'],
            'passengers_served': ['mean', 'sum'],
            'passengers_left_behind': ['mean', 'sum'],
            'avg_occupancy_rate': 'mean',
            'avg_train_delay_sec': 'mean',
            'delay_propagation_count': 'mean',
            'failed_trains': 'sum',
            'total_system_cost': 'mean'
        }).round(2)
        return summary
    
    def plot_waiting_time_heatmap(self, ax=None):
        """Heatmap: avg waiting time by config and scenario"""
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 7))
        
        pivot = self.df.pivot_table(
            values='avg_waiting_time_sec', 
            index='config_name', 
            columns='scenario_name',
            aggfunc='mean'
        )
        
        sns.heatmap(pivot, annot=True, fmt='.1f', cmap='RdYlGn_r', ax=ax, 
                    cbar_kws={'label': 'Avg Waiting Time (sec)'})
        ax.set_title('Passenger Waiting Time by Configuration & Scenario', 
                    fontsize=13, fontweight='bold', pad=15)
        ax.set_xlabel('Scenario', fontsize=11)
        ax.set_ylabel('Train Configuration', fontsize=11)
        return ax
    
    def plot_system_cost_heatmap(self, ax=None):
        """Heatmap: total system cost by config and scenario"""
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 7))
        
        pivot = self.df.pivot_table(
            values='total_system_cost', 
            index='config_name', 
            columns='scenario_name',
            aggfunc='mean'
        )
        
        sns.heatmap(pivot, annot=True, fmt='.2f', cmap='RdYlGn_r', ax=ax,
                    cbar_kws={'label': 'Total System Cost'})
        ax.set_title('Total System Cost by Configuration & Scenario', 
                    fontsize=13, fontweight='bold', pad=15)
        ax.set_xlabel('Scenario', fontsize=11)
        ax.set_ylabel('Train Configuration', fontsize=11)
        return ax
    
    def plot_passengers_left_behind(self, ax=None):
        """Stacked bar: passengers left behind"""
        if ax is None:
            fig, ax = plt.subplots(figsize=(14, 6))
        
        pivot = self.df.pivot_table(
            values='passengers_left_behind', 
            index='scenario_name', 
            columns='config_name',
            aggfunc='mean'
        )
        
        pivot.plot(kind='bar', ax=ax, width=0.7)
        ax.set_title('Passengers Left Behind (Unserved) by Configuration & Scenario', 
                    fontsize=13, fontweight='bold', pad=15)
        ax.set_xlabel('Scenario', fontsize=11)
        ax.set_ylabel('Avg Passengers per Hour', fontsize=11)
        ax.legend(title='Configuration', bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
        ax.grid(axis='y', alpha=0.3)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        return ax
    
    def plot_occupancy_rates(self, ax=None):
        """Occupancy rate analysis"""
        if ax is None:
            fig, ax = plt.subplots(figsize=(14, 6))
        
        pivot = self.df.pivot_table(
            values='avg_occupancy_rate', 
            index='scenario_name', 
            columns='config_name',
            aggfunc='mean'
        )
        
        pivot.plot(kind='bar', ax=ax, width=0.7)
        ax.axhline(y=0.85, color='red', linestyle='--', linewidth=2, label='Comfort Threshold (85%)')
        ax.set_title('Average Train Occupancy Rate by Configuration & Scenario', 
                    fontsize=13, fontweight='bold', pad=15)
        ax.set_xlabel('Scenario', fontsize=11)
        ax.set_ylabel('Occupancy Rate', fontsize=11)
        ax.set_ylim(0, 1.05)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
        ax.grid(axis='y', alpha=0.3)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        return ax
    
    def plot_delay_propagation(self, ax=None):
        """Delay propagation analysis"""
        if ax is None:
            fig, ax = plt.subplots(figsize=(14, 6))
        
        pivot = self.df.pivot_table(
            values='delay_propagation_count', 
            index='scenario_name', 
            columns='config_name',
            aggfunc='mean'
        )
        
        pivot.plot(kind='bar', ax=ax, width=0.7)
        ax.set_title('Average Delay Propagation Events by Configuration & Scenario', 
                    fontsize=13, fontweight='bold', pad=15)
        ax.set_xlabel('Scenario', fontsize=11)
        ax.set_ylabel('Propagated Delays per Run', fontsize=11)
        ax.legend(title='Configuration', bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=9)
        ax.grid(axis='y', alpha=0.3)
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        return ax
    
    def plot_pareto_frontier(self, scenario_name=None, ax=None):
        """Pareto frontier: waiting time vs system cost"""
        if ax is None:
            fig, ax = plt.subplots(figsize=(12, 8))
        
        if scenario_name:
            data = self.df[self.df['scenario_name'] == scenario_name]
            title_suffix = f" ({scenario_name})"
        else:
            data = self.df
            title_suffix = ""
        
        # Group by config and take mean
        grouped = data.groupby('config_name').agg({
            'avg_waiting_time_sec': 'mean',
            'total_system_cost': 'mean',
            'passengers_served': 'sum'
        }).reset_index()
        
        colors = ['red' if '3-car' in name else 'blue' for name in grouped['config_name']]
        sizes = grouped['passengers_served'] / 10
        
        for idx, row in grouped.iterrows():
            ax.scatter(row['avg_waiting_time_sec'], row['total_system_cost'], 
                      s=sizes.iloc[idx], alpha=0.6, c=[colors[idx]], 
                      edgecolors='black', linewidth=1.5)
            ax.annotate(row['config_name'], 
                       (row['avg_waiting_time_sec'], row['total_system_cost']),
                       fontsize=9, ha='center', fontweight='bold')
        
        ax.set_xlabel('Avg Passenger Waiting Time (sec)', fontsize=12, fontweight='bold')
        ax.set_ylabel('Total System Cost', fontsize=12, fontweight='bold')
        ax.set_title(f'Pareto Frontier: Waiting Time vs System Cost{title_suffix}', 
                    fontsize=13, fontweight='bold', pad=15)
        ax.grid(True, alpha=0.3)
        return ax
    
    def plot_robustness_analysis(self, ax=None):
        """Robustness: how configs handle disruptions"""
        if ax is None:
            fig, ax = plt.subplots(figsize=(14, 6))
        
        # Group by config and scenario type
        scenarios_severe = ['SURGE\n(Very High)', 'DISRUPTION\n(Delays + Surge)', 'CASCADING\n(Failures + Delays)']
        
        robustness_data = []
        for config in self.df['config_name'].unique():
            config_data = self.df[self.df['config_name'] == config]
            
            normal_cost = config_data[config_data['scenario_name'] == 'NORMAL\n(Moderate, Typical)']['total_system_cost'].mean()
            severe_cost = config_data[config_data['scenario_name'].isin(scenarios_severe)]['total_system_cost'].mean()
            
            cost_increase = ((severe_cost - normal_cost) / normal_cost * 100) if normal_cost > 0 else 0
            
            robustness_data.append({
                'config': config,
                'cost_increase_pct': cost_increase
            })
        
        robustness_df = pd.DataFrame(robustness_data).sort_values('cost_increase_pct')
        
        colors_robust = ['green' if x < 25 else 'orange' if x < 50 else 'red' 
                        for x in robustness_df['cost_increase_pct']]
        
        ax.barh(robustness_df['config'], robustness_df['cost_increase_pct'], color=colors_robust)
        ax.set_xlabel('Cost Increase from Normal to Severe Scenarios (%)', fontsize=12, fontweight='bold')
        ax.set_title('Robustness Analysis: Which Config Handles Disruptions Best?', 
                    fontsize=13, fontweight='bold', pad=15)
        ax.grid(axis='x', alpha=0.3)
        
        for idx, (config, cost) in enumerate(zip(robustness_df['config'], robustness_df['cost_increase_pct'])):
            ax.text(cost + 1, idx, f'{cost:.1f}%', va='center', fontsize=9, fontweight='bold')
        
        return ax
    
    def plot_scenario_surface(self, config_name, ax=None):
        """3D surface: demand vs cost for specific config"""
        if ax is None:
            fig = plt.figure(figsize=(12, 7))
            ax = fig.add_subplot(111, projection='3d')
        
        data = self.df[self.df['config_name'] == config_name].copy()
        
        # Create demand levels from scenario names
        demand_map = {
            'OFF-PEAK\n(Low, Stable)': 0.5,
            'NORMAL\n(Moderate, Typical)': 1.0,
            'PEAK\n(High, Busy)': 2.0,
            'SURGE\n(Very High)': 3.0,
            'DISRUPTION\n(Delays + Surge)': 2.5,
            'CASCADING\n(Failures + Delays)': 1.5
        }
        
        data['demand_level'] = data['scenario_name'].map(demand_map)
        data['occupancy_pct'] = data['avg_occupancy_rate'] * 100
        
        from mpl_toolkits.mplot3d import Axes3D
        
        scatter = ax.scatter(data['demand_level'], data['occupancy_pct'], 
                            data['total_system_cost'], c=data['total_system_cost'],
                            cmap='RdYlGn_r', s=100, alpha=0.6, edgecolors='black')
        
        ax.set_xlabel('Demand Level', fontsize=10, fontweight='bold')
        ax.set_ylabel('Occupancy (%)', fontsize=10, fontweight='bold')
        ax.set_zlabel('System Cost', fontsize=10, fontweight='bold')
        ax.set_title(f'Cost Landscape: {config_name}', fontsize=12, fontweight='bold')
        
        return ax

def main():
    print("=" * 80)
    print("METRO CAPACITY OPTIMIZATION SIMULATION")
    print("Comprehensive Monte Carlo Analysis: 3-car vs 6-car vs Hybrid Strategies")
    print("=" * 80)
    print()
    
    # Create configurations and scenarios
    configs = create_train_configs()
    scenarios = create_scenarios()
    
    print(f"Testing {len(configs)} train configurations across {len(scenarios)} scenarios")
    print(f"Each configuration-scenario pair: 100 simulation runs")
    print(f"Total simulations: {len(configs) * len(scenarios) * 100:,}")
    print()
    
    # Run all simulations
    all_results = []
    total_sims = len(configs) * len(scenarios)
    current_sim = 0
    
    for config in configs:
        for scenario in scenarios:
            current_sim += 1
            print(f"[{current_sim:2d}/{total_sims}] Running: {config.name:15s} × {scenario.name:30s}...", 
                  end='\r', flush=True)
            
            sim = MetroSimulation(config, scenario, simulation_time_hours=1.0, num_simulations=100)
            results = sim.run()
            all_results.extend(results)
    
    print("\nSimulation complete!")
    print(f"Total results collected: {len(all_results):,}")
    print()
    
    # Analyze results
    analysis = SimulationAnalysis(all_results)
    
    # Create comprehensive figures
    print("Generating visualizations...")
    print()
    
    # Figure 1: Key Heatmaps
    fig1 = plt.figure(figsize=(18, 12))
    
    ax1 = plt.subplot(2, 2, 1)
    analysis.plot_waiting_time_heatmap(ax1)
    
    ax2 = plt.subplot(2, 2, 2)
    analysis.plot_system_cost_heatmap(ax2)
    
    ax3 = plt.subplot(2, 2, 3)
    analysis.plot_occupancy_rates(ax3)
    
    ax4 = plt.subplot(2, 2, 4)
    analysis.plot_delay_propagation(ax4)
    
    plt.tight_layout()
    plt.savefig('/mnt/user-data/outputs/01_heatmaps_and_analysis.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: 01_heatmaps_and_analysis.png")
    
    # Figure 2: Unserved Passengers
    fig2 = plt.figure(figsize=(16, 7))
    analysis.plot_passengers_left_behind(plt.gca())
    plt.tight_layout()
    plt.savefig('/mnt/user-data/outputs/02_passengers_left_behind.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: 02_passengers_left_behind.png")
    
    # Figure 3: Pareto Frontier
    fig3 = plt.figure(figsize=(12, 8))
    analysis.plot_pareto_frontier(ax=plt.gca())
    plt.tight_layout()
    plt.savefig('/mnt/user-data/outputs/03_pareto_frontier.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: 03_pareto_frontier.png")
    
    # Figure 4: Pareto by Scenario
    scenarios_to_plot = ['NORMAL\n(Moderate, Typical)', 'PEAK\n(High, Busy)', 'DISRUPTION\n(Delays + Surge)']
    fig4 = plt.figure(figsize=(18, 5))
    for idx, scenario_name in enumerate(scenarios_to_plot):
        ax = plt.subplot(1, 3, idx + 1)
        analysis.plot_pareto_frontier(scenario_name=scenario_name, ax=ax)
    plt.tight_layout()
    plt.savefig('/mnt/user-data/outputs/04_pareto_by_scenario.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: 04_pareto_by_scenario.png")
    
    # Figure 5: Robustness Analysis
    fig5 = plt.figure(figsize=(14, 8))
    analysis.plot_robustness_analysis(plt.gca())
    plt.tight_layout()
    plt.savefig('/mnt/user-data/outputs/05_robustness_analysis.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: 05_robustness_analysis.png")
    
    # Figure 6: Scenario Surfaces (example configs)
    example_configs = ['3-car / 1.5 min', '6-car / 3.0 min', '6-car / 2.5 min']
    fig6 = plt.figure(figsize=(18, 5))
    for idx, config_name in enumerate(example_configs):
        ax = fig6.add_subplot(1, 3, idx + 1, projection='3d')
        analysis.plot_scenario_surface(config_name, ax=ax)
    plt.tight_layout()
    plt.savefig('/mnt/user-data/outputs/06_scenario_surfaces_3d.png', dpi=300, bbox_inches='tight')
    print("✓ Saved: 06_scenario_surfaces_3d.png")
    
    # Export detailed summary table
    summary = analysis.create_summary_table()
    summary.to_csv('/mnt/user-data/outputs/simulation_summary_statistics.csv')
    print("✓ Saved: simulation_summary_statistics.csv")
    
    # Export full results
    analysis.df.to_csv('/mnt/user-data/outputs/full_simulation_results.csv', index=False)
    print("✓ Saved: full_simulation_results.csv")
    
    print()
    print("=" * 80)
    print("RECOMMENDATION SUMMARY")
    print("=" * 80)
    print()
    
    # Find best configuration overall (weighted score)
    df_mean = analysis.df.groupby('config_name').agg({
        'avg_waiting_time_sec': 'mean',
        'total_system_cost': 'mean',
        'passengers_left_behind': 'mean',
        'avg_occupancy_rate': 'mean'
    }).reset_index()
    
    # Normalize scores (0-1) and compute weighted aggregate
    df_mean['waiting_norm'] = (df_mean['avg_waiting_time_sec'] - df_mean['avg_waiting_time_sec'].min()) / \
                              (df_mean['avg_waiting_time_sec'].max() - df_mean['avg_waiting_time_sec'].min())
    df_mean['cost_norm'] = (df_mean['total_system_cost'] - df_mean['total_system_cost'].min()) / \
                          (df_mean['total_system_cost'].max() - df_mean['total_system_cost'].min())
    df_mean['unserved_norm'] = (df_mean['passengers_left_behind'] - df_mean['passengers_left_behind'].min()) / \
                               (df_mean['passengers_left_behind'].max() - df_mean['passengers_left_behind'].min())
    
    df_mean['score'] = (0.33 * df_mean['waiting_norm'] + 
                        0.33 * df_mean['cost_norm'] + 
                        0.34 * df_mean['unserved_norm'])
    
    df_mean_sorted = df_mean.sort_values('score')
    
    print("TOP 5 CONFIGURATIONS (by aggregate score):")
    print()
    for idx, row in df_mean_sorted.head(5).iterrows():
        print(f"  #{idx+1}: {row['config_name']:20s}")
        print(f"       Avg Waiting Time: {row['avg_waiting_time_sec']:6.1f} sec")
        print(f"       System Cost:      {row['total_system_cost']:6.2f}")
        print(f"       Unserved/hour:    {row['passengers_left_behind']:6.1f}")
        print()
    
    # Peak scenario analysis
    peak_data = analysis.df[analysis.df['scenario_name'] == 'PEAK\n(High, Busy)']
    peak_best = peak_data.groupby('config_name')['total_system_cost'].mean().idxmin()
    
    print(f"BEST FOR PEAK SCENARIO: {peak_best}")
    print()
    
    # Disruption scenario analysis
    disruption_data = analysis.df[analysis.df['scenario_name'].isin(
        ['DISRUPTION\n(Delays + Surge)', 'CASCADING\n(Failures + Delays)']
    )]
    disruption_best = disruption_data.groupby('config_name')['total_system_cost'].mean().idxmin()
    
    print(f"BEST FOR DISRUPTION SCENARIOS: {disruption_best}")
    print()
    
    print("=" * 80)
    print()


if __name__ == "__main__":
    main()
