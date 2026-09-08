import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

df = pd.read_csv('full_simulation_results.csv')

class AnalysisToolkit:
    def __init__(self, results_df):
        self.df = results_df
        
    def compare_configs(self, config1, config2, scenario=None):
        d1 = self.df[self.df['config_name'] == config1]
        d2 = self.df[self.df['config_name'] == config2]
        
        if scenario:
            d1 = d1[d1['scenario_name'] == scenario]
            d2 = d2[d2['scenario_name'] == scenario]
        
        metrics = ['avg_waiting_time_sec', 'total_system_cost', 'passengers_served', 
                   'passengers_left_behind', 'avg_occupancy_rate', 'avg_train_delay_sec']
        print(f"COMPARISON: {config1} vs {config2}")
        if scenario:
            print(f"Scenario: {scenario}")
        print(f"{'Metric':<30} {'Config 1':>15} {'Config 2':>15} {'Difference':>10}")

        
        for metric in metrics:
            val1 = d1[metric].mean()
            val2 = d2[metric].mean()
            diff = ((val2 - val1) / val1 * 100) if val1 != 0 else 0
            
            print(f"{metric:<30} {val1:>15.2f} {val2:>15.2f} {diff:>9.1f}%")
    
    def scenario_stress_test(self, config_name):
        data = self.df[self.df['config_name'] == config_name]
        scenarios_ranked = data.groupby('scenario_name')['total_system_cost'].mean().sort_values()
        
        for scenario, cost in scenarios_ranked.items():
            scenario_data = data[data['scenario_name'] == scenario]
            wait = scenario_data['avg_waiting_time_sec'].mean()
            unserved = scenario_data['passengers_left_behind'].mean()
            occ = scenario_data['avg_occupancy_rate'].mean()
                        print(f"\n{scenario}")
            print(f"  Cost: {cost:8.2f} | Wait: {wait:6.1f}s | Unserved: {unserved:7.0f} | Occ: {occ:5.1%}")
    
    def find_best_for_scenario(self, scenario_name, metric='total_system_cost'):
        data = self.df[self.df['scenario_name'] == scenario_name]
        best = data.groupby('config_name')[metric].mean().idxmin()
        return best
    
    def occupancy_analysis(self):
        print(f"\n{'='*70}")
        print("OCCUPANCY ANALYSIS")
        print(f"{'='*70}")
                occ_by_config = self.df.groupby('config_name')['avg_occupancy_rate'].agg(['mean', 'std', 'min', 'max'])
        occ_by_config = occ_by_config * 100
                print(f"{'Config':<20} {'Mean %':>10} {'Std %':>10} {'Min %':>10} {'Max %':>10}")
        print(f"{'-'*70}")
        for config, row in occ_by_config.iterrows():
            print(f"{config:<20} {row['mean']:>10.1f} {row['std']:>10.1f} {row['min']:>10.1f} {row['max']:>10.1f}")
        
        print(f"Optimal occupancy: 70-85% (balance of capacity & comfort)")
        print(f"Below 70%: Wasteful (too many trains)")
        print(f"Above 85%: Uncomfortable (crowding risk)")
    
    def cost_breakdown(self, config_name, scenario_name):
        data = self.df[(self.df['config_name'] == config_name) & 
                       (self.df['scenario_name'] == scenario_name)]
        
        mean_data = data.iloc[0] if len(data) > 0 else None
        
        if mean_data is None:
            print(f"No data for {config_name} in {scenario_name}")
            return
        print(f"COST BREAKDOWN: {config_name} × {scenario_name}")
        
        print(f"Waiting time cost:        {data['avg_waiting_time_sec'].mean():>8.1f} sec/pass")
        print(f"Passengers left behind:   {data['passengers_left_behind'].mean():>8.0f} /hour")
        print(f"Train delay:              {data['avg_train_delay_sec'].mean():>8.1f} sec/train")
        print(f"Delay propagation events: {data['delay_propagation_count'].mean():>8.1f} /run")
        print(f"Failed trains:            {data['failed_trains'].mean():>8.1f} /run")
        print(f"Total system cost:        {data['total_system_cost'].mean():>8.2f}")
    
    def headway_sensitivity(self):
        print(f"\n{'='*70}")
        print("HEADWAY SENSITIVITY ANALYSIS")
        print(f"{'='*70}")
        print(f"\nHow waiting time changes with headway:")
        print(f"{'Config':<20} {'Headway':>10} {'Avg Wait':>12} {'Max Wait':>12}")
        print(f"{'-'*70}")
        
        for config in self.df['config_name'].unique():
            data = self.df[self.df['config_name'] == config]
            headway = config.split('/')[-1].replace(' min', '')
            wait_avg = data['avg_waiting_time_sec'].mean()
            wait_max = data['max_waiting_time_sec'].mean()
            
            print(f"{config:<20} {headway:>10} {wait_avg:>12.1f} {wait_max:>12.1f}")
    
    def resilience_score(self):
        scores = []
        for config in self.df['config_name'].unique():
            data = self.df[self.df['config_name'] == config]
            wait_score = (data['avg_waiting_time_sec'].max() - data['avg_waiting_time_sec'].mean()) / data['avg_waiting_time_sec'].max() * 10
            cap_score = (10 - data['passengers_left_behind'].mean() / data['passengers_left_behind'].max() * 10)
            stab_score = (10 - data['delay_propagation_count'].mean() / data['delay_propagation_count'].max() * 10)
            
            overall = (wait_score + cap_score + stab_score) / 3
            
            scores.append({
                'config': config,
                'waiting': wait_score,
                'capacity': cap_score,
                'stability': stab_score,
                'overall': overall
            })
        
        scores_df = pd.DataFrame(scores).sort_values('overall', ascending=False)
        
        for _, row in scores_df.iterrows():
            print(f"{row['config']:<20} {row['waiting']:>8.1f} {row['capacity']:>8.1f} {row['stability']:>10.1f} {row['overall']:>8.1f}")
    
    def peak_hour_analysis(self):      
        peak = self.df[self.df['scenario_name'] == 'PEAK\n(High, Busy)']

        by_config = peak.groupby('config_name').agg({
            'total_system_cost': 'mean',
            'avg_waiting_time_sec': 'mean',
            'passengers_left_behind': 'mean',
            'avg_occupancy_rate': 'mean'
        }).sort_values('total_system_cost')
        
        for config, row in by_config.iterrows():
            print(f"{config:<20} {row['total_system_cost']:>10.2f} {row['avg_waiting_time_sec']:>8.1f} {row['passengers_left_behind']:>10.0f} {row['avg_occupancy_rate']*100:>7.1f}")

def interactive_menu():
    toolkit = AnalysisToolkit(df)
    while True:
        print("1. Compare two configurations")
        print("2. Stress test a configuration")
        print("3. Find best config for scenario")
        print("4. Occupancy analysis")
        print("5. Cost breakdown")
        print("6. Headway sensitivity")
        print("7. Resilience scorecard")
        print("8. Peak hour analysis")
        
        choice = input("Select option (1-9): ").strip()
        
        if choice == '1':
            print("\nAvailable configurations:")
            for i, config in enumerate(df['config_name'].unique(), 1):
                print(f"  {i}. {config}")
            
            c1 = input("Enter first config name: ").strip()
            c2 = input("Enter second config name: ").strip()
            scenario = input("Enter scenario (or leave blank for all): ").strip()
            scenario = scenario if scenario else None
            
            toolkit.compare_configs(c1, c2, scenario)
        
        elif choice == '2':
            config = input("Enter config name: ").strip()
            toolkit.scenario_stress_test(config)
        
        elif choice == '3':
            scenario = input("Enter scenario name: ").strip()
            toolkit.find_best_for_scenario(scenario)
        
        elif choice == '4':
            toolkit.occupancy_analysis()
        
        elif choice == '5':
            config = input("Enter config name: ").strip()
            scenario = input("Enter scenario name: ").strip()
            toolkit.cost_breakdown(config, scenario)
        
        elif choice == '6':
            toolkit.headway_sensitivity()
        
        elif choice == '7':
            toolkit.resilience_score()
        
        elif choice == '8':
            toolkit.peak_hour_analysis()
        
        elif choice == '9':
            print("Exiting...")
            break


if __name__ == "__main__":
    print("\n" + "="*70)
    print("METRO SIMULATION RESULTS LOADED")
    print("="*70)
    print(f"Total simulations: {len(df):,}")
    print(f"Configurations: {df['config_name'].nunique()}")
    print(f"Scenarios: {df['scenario_name'].nunique()}")
    print("\nAvailable configurations:")
    for config in sorted(df['config_name'].unique()):
        print(f"  - {config}")

    interactive_menu()
