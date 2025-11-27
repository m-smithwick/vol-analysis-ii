"""
Test Regime Chart Rendering

This test isolates the regime shading issue by creating controlled test scenarios
with known regime patterns to verify visual rendering in Plotly charts.
"""

import pandas as pd
import sys
import os
sys.path.insert(0, os.path.abspath('..'))

from chart_builder_plotly import generate_analysis_chart


def load_test_data():
    """Load last 30 days of APP data from Excel file."""
    excel_path = '../results_volume/APP_6mo_20231127_20251125_data.xlsx'
    
    # Load the Analysis_Data sheet
    df = pd.read_excel(excel_path, sheet_name='Analysis_Data')
    
    # Set Date as index
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    
    # Get last 30 rows
    df_test = df.tail(30).copy()
    
    print(f"✅ Loaded {len(df_test)} days of test data")
    print(f"   Date range: {df_test.index[0].strftime('%Y-%m-%d')} to {df_test.index[-1].strftime('%Y-%m-%d')}")
    
    return df_test


def create_scenario_a(df):
    """Scenario A: Last day ONLY is TRUE (rest FALSE)."""
    df_test = df.copy()
    df_test['Overall_Regime_OK'] = False
    df_test.iloc[-1, df_test.columns.get_loc('Overall_Regime_OK')] = True
    
    print(f"\n📊 SCENARIO A: Last day only GREEN")
    print(f"   FALSE days: {(~df_test['Overall_Regime_OK']).sum()}")
    print(f"   TRUE days: {df_test['Overall_Regime_OK'].sum()}")
    print(f"   Last 5 days regime: {df_test['Overall_Regime_OK'].tail(5).tolist()}")
    
    return df_test


def create_scenario_b(df):
    """Scenario B: Last 3 days are TRUE."""
    df_test = df.copy()
    df_test['Overall_Regime_OK'] = False
    df_test.iloc[-3:, df_test.columns.get_loc('Overall_Regime_OK')] = True
    
    print(f"\n📊 SCENARIO B: Last 3 days GREEN")
    print(f"   FALSE days: {(~df_test['Overall_Regime_OK']).sum()}")
    print(f"   TRUE days: {df_test['Overall_Regime_OK'].sum()}")
    print(f"   Last 5 days regime: {df_test['Overall_Regime_OK'].tail(5).tolist()}")
    
    return df_test


def create_scenario_c(df):
    """Scenario C: Alternating TRUE/FALSE pattern."""
    df_test = df.copy()
    # Create alternating pattern: FALSE, TRUE, FALSE, TRUE, ...
    df_test['Overall_Regime_OK'] = [i % 2 == 1 for i in range(len(df_test))]
    
    print(f"\n📊 SCENARIO C: Alternating pattern")
    print(f"   FALSE days: {(~df_test['Overall_Regime_OK']).sum()}")
    print(f"   TRUE days: {df_test['Overall_Regime_OK'].sum()}")
    print(f"   Last 5 days regime: {df_test['Overall_Regime_OK'].tail(5).tolist()}")
    
    return df_test


def create_scenario_d(df):
    """Scenario D: All TRUE (all GREEN)."""
    df_test = df.copy()
    df_test['Overall_Regime_OK'] = True
    
    print(f"\n📊 SCENARIO D: All days GREEN")
    print(f"   TRUE days: {df_test['Overall_Regime_OK'].sum()}")
    
    return df_test


def main():
    print("="*60)
    print("REGIME CHART RENDERING TEST")
    print("="*60)
    
    # Load base data
    df_base = load_test_data()
    
    # Create test scenarios
    scenarios = [
        ('A_last_day_only', create_scenario_a(df_base)),
        ('B_last_3_days', create_scenario_b(df_base)),
        ('C_alternating', create_scenario_c(df_base)),
        ('D_all_green', create_scenario_d(df_base))
    ]
    
    # Generate charts for each scenario
    print(f"\n{'='*60}")
    print("GENERATING TEST CHARTS")
    print(f"{'='*60}")
    
    for scenario_name, df_scenario in scenarios:
        try:
            output_path = f"../results_volume/TEST_{scenario_name}_regime.html"
            
            print(f"\n📈 Generating chart for scenario: {scenario_name}")
            generate_analysis_chart(
                df=df_scenario,
                ticker=f"TEST_{scenario_name}",
                period="30d",
                save_path=output_path,
                show=False
            )
            
            print(f"   ✅ Saved to: {output_path}")
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    print(f"\n{'='*60}")
    print("✅ TEST COMPLETE")
    print(f"{'='*60}")
    print("\n📂 Open the generated HTML files to verify regime shading:")
    print("   - Scenario A: Last bar should be GREEN, rest RED")
    print("   - Scenario B: Last 3 bars should be GREEN, rest RED")
    print("   - Scenario C: Alternating RED/GREEN bars")
    print("   - Scenario D: All bars should be GREEN")
    print("\n💡 If last bar(s) show RED when they should be GREEN,")
    print("   the issue is confirmed in the Plotly rendering logic.")


if __name__ == "__main__":
    main()
