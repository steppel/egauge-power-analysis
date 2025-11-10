#!/usr/bin/env python3
"""
eGauge Power Monitor Analysis Script
Analyzes power consumption and solar production data from eGauge device
"""

import requests
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import seaborn as sns
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')

# Configuration
EGAUGE_IP = "10.10.20.241"
BASE_URL = f"http://{EGAUGE_IP}/cgi-bin/egauge-show"

# Set style for better-looking plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

class EGaugeAnalyzer:
    def __init__(self, ip_address: str):
        self.ip = ip_address
        self.base_url = f"http://{ip_address}/cgi-bin/egauge-show"

    def fetch_historical_data(self, days_back: int = 365) -> pd.DataFrame:
        """
        Fetch historical data from eGauge for specified number of days
        """
        print(f"Fetching {days_back} days of historical data from eGauge at {self.ip}...")

        # Calculate timestamps
        end_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=days_back)).timestamp())

        # For one year of data, use appropriate granularity (hourly data)
        # eGauge supports different time intervals: S (second), m (minute), h (hour), d (day)
        params = {
            'h': '',  # Request hourly data
            'n': 24 * days_back,  # Number of rows (24 hours * days)
            'f': start_time,  # From timestamp
            't': end_time,  # To timestamp
            'C': '',  # Compressed format
        }

        # Construct URL
        url = f"{self.base_url}?h&n={params['n']}&f={params['f']}"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            # Parse XML response
            root = ET.fromstring(response.content)

            # Extract data
            data_points = []

            # Get register names and units
            registers = {}
            for reg in root.findall('.//cname'):
                reg_id = reg.get('t')
                reg_name = reg.text
                registers[reg_id] = reg_name

            # Process each data row
            for row in root.findall('.//r'):
                timestamp = int(row.find('t').text)
                dt = datetime.fromtimestamp(timestamp)

                row_data = {'timestamp': dt}

                for col in row.findall('c'):
                    col_id = col.get('r')
                    if col_id in registers:
                        # Convert from Wh to kWh
                        value = float(col.text) / 1000.0 if col.text else 0
                        row_data[registers[col_id]] = value

                data_points.append(row_data)

            df = pd.DataFrame(data_points)
            if not df.empty:
                df = df.set_index('timestamp')
                df = df.sort_index()

                # Calculate net values
                if 'Grid+' in df.columns and 'Grid' in df.columns:
                    df['Grid_Net'] = df['Grid'] - df['Grid+']

                if 'Solar+' in df.columns and 'Solar' in df.columns:
                    df['Solar_Net'] = df['Solar+'] - df['Solar']

                print(f"Successfully fetched {len(df)} data points")
                return df
            else:
                print("No data received from eGauge")
                return pd.DataFrame()

        except Exception as e:
            print(f"Error fetching data: {e}")
            # Try alternative method with instantaneous values
            return self.fetch_instant_data_series(days_back)

    def fetch_instant_data_series(self, days_back: int) -> pd.DataFrame:
        """
        Alternative method to fetch data using instant readings
        """
        print("Trying alternative data fetch method...")
        data_points = []

        # Sample data points (every 6 hours for the last year)
        sample_interval_hours = 6
        total_samples = (days_back * 24) // sample_interval_hours

        for i in range(0, min(total_samples, 1460)):  # Limit to avoid too many requests
            hours_ago = i * sample_interval_hours
            timestamp = datetime.now() - timedelta(hours=hours_ago)

            try:
                url = f"http://{self.ip}/cgi-bin/egauge?inst"
                response = requests.get(url, timeout=5)

                if response.status_code == 200:
                    root = ET.fromstring(response.content)

                    row_data = {'timestamp': timestamp}

                    for reg in root.findall('.//r'):
                        name = reg.get('n')
                        power_element = reg.find('i')
                        if power_element is not None:
                            power = float(power_element.text) / 1000.0  # Convert to kW
                            row_data[name] = power

                    data_points.append(row_data)

                    if i % 100 == 0:
                        print(f"Fetched {i}/{total_samples} samples...")

            except Exception as e:
                continue

        df = pd.DataFrame(data_points)
        if not df.empty:
            df = df.set_index('timestamp')
            df = df.sort_index()

        return df

    def analyze_monthly_patterns(self, df: pd.DataFrame) -> Dict:
        """
        Analyze month-over-month consumption and solar production
        """
        print("\nAnalyzing monthly patterns...")

        if df.empty:
            return {}

        # Resample to daily for calculations
        daily_df = df.resample('D').mean()

        # Calculate monthly statistics
        monthly_stats = {}

        for col in df.columns:
            if 'Grid' in col or 'Solar' in col:
                monthly = df[col].resample('M').agg(['mean', 'sum', 'max', 'min'])
                monthly_stats[col] = monthly

        # Create monthly summary
        summary = pd.DataFrame()

        if 'Grid' in df.columns:
            summary['Grid_Import_kWh'] = df['Grid'].resample('M').sum()
        if 'Grid+' in df.columns:
            summary['Grid_Export_kWh'] = df['Grid+'].resample('M').sum()
        if 'Solar' in df.columns:
            summary['Solar_Production_kWh'] = df['Solar'].resample('M').sum()

        # Calculate net import/export
        if 'Grid_Import_kWh' in summary.columns and 'Grid_Export_kWh' in summary.columns:
            summary['Net_Grid_kWh'] = summary['Grid_Import_kWh'] - summary['Grid_Export_kWh']

        return {
            'monthly_summary': summary,
            'monthly_stats': monthly_stats
        }

    def analyze_hourly_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Analyze hourly usage patterns
        """
        print("\nAnalyzing hourly usage patterns...")

        if df.empty:
            return pd.DataFrame()

        # Extract hour of day
        df_hourly = df.copy()
        df_hourly['hour'] = df_hourly.index.hour
        df_hourly['day_of_week'] = df_hourly.index.dayofweek
        df_hourly['month'] = df_hourly.index.month

        # Calculate hourly averages
        hourly_avg = df_hourly.groupby('hour').mean()

        # Calculate weekday vs weekend patterns
        df_hourly['is_weekend'] = df_hourly['day_of_week'].isin([5, 6])
        weekday_hourly = df_hourly[~df_hourly['is_weekend']].groupby('hour').mean()
        weekend_hourly = df_hourly[df_hourly['is_weekend']].groupby('hour').mean()

        return {
            'hourly_avg': hourly_avg,
            'weekday_hourly': weekday_hourly,
            'weekend_hourly': weekend_hourly,
            'df_hourly': df_hourly
        }

    def create_visualizations(self, df: pd.DataFrame, monthly_data: Dict, hourly_data: Dict):
        """
        Create comprehensive visualizations
        """
        print("\nCreating visualizations...")

        # Create figure with subplots
        fig = plt.figure(figsize=(20, 24))

        # 1. Time series plot of grid and solar
        ax1 = plt.subplot(6, 2, 1)
        if 'Grid' in df.columns:
            ax1.plot(df.index, df['Grid'], label='Grid Import', alpha=0.7)
        if 'Grid+' in df.columns:
            ax1.plot(df.index, df['Grid+'], label='Grid Export', alpha=0.7)
        if 'Solar' in df.columns:
            ax1.plot(df.index, df['Solar'], label='Solar Production', alpha=0.7)
        ax1.set_title('Power Flow Over Time', fontsize=14, fontweight='bold')
        ax1.set_xlabel('Date')
        ax1.set_ylabel('Power (kW)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 2. Monthly consumption bar chart
        ax2 = plt.subplot(6, 2, 2)
        if 'monthly_summary' in monthly_data and not monthly_data['monthly_summary'].empty:
            summary = monthly_data['monthly_summary']
            months = summary.index.strftime('%b %Y')
            x = np.arange(len(months))
            width = 0.35

            if 'Grid_Import_kWh' in summary.columns:
                ax2.bar(x - width/2, summary['Grid_Import_kWh'], width, label='Grid Import', color='red', alpha=0.7)
            if 'Solar_Production_kWh' in summary.columns:
                ax2.bar(x + width/2, summary['Solar_Production_kWh'], width, label='Solar Production', color='green', alpha=0.7)

            ax2.set_xlabel('Month')
            ax2.set_ylabel('Energy (kWh)')
            ax2.set_title('Monthly Energy Summary', fontsize=14, fontweight='bold')
            ax2.set_xticks(x)
            ax2.set_xticklabels(months, rotation=45, ha='right')
            ax2.legend()
            ax2.grid(True, alpha=0.3)

        # 3. Hourly usage pattern
        ax3 = plt.subplot(6, 2, 3)
        if hourly_data and 'hourly_avg' in hourly_data:
            hourly_avg = hourly_data['hourly_avg']
            hours = hourly_avg.index

            if 'Grid' in hourly_avg.columns:
                ax3.plot(hours, hourly_avg['Grid'], marker='o', label='Grid Import', linewidth=2)
            if 'Solar' in hourly_avg.columns:
                ax3.plot(hours, hourly_avg['Solar'], marker='s', label='Solar Production', linewidth=2)

            ax3.set_xlabel('Hour of Day')
            ax3.set_ylabel('Average Power (kW)')
            ax3.set_title('Average Hourly Power Pattern', fontsize=14, fontweight='bold')
            ax3.set_xticks(range(0, 24, 2))
            ax3.legend()
            ax3.grid(True, alpha=0.3)

        # 4. Weekday vs Weekend patterns
        ax4 = plt.subplot(6, 2, 4)
        if hourly_data and 'weekday_hourly' in hourly_data:
            weekday = hourly_data['weekday_hourly']
            weekend = hourly_data['weekend_hourly']

            if 'Grid' in weekday.columns:
                ax4.plot(weekday.index, weekday['Grid'], label='Weekday', linewidth=2, marker='o')
                ax4.plot(weekend.index, weekend['Grid'], label='Weekend', linewidth=2, marker='s')

            ax4.set_xlabel('Hour of Day')
            ax4.set_ylabel('Average Grid Import (kW)')
            ax4.set_title('Weekday vs Weekend Usage Patterns', fontsize=14, fontweight='bold')
            ax4.legend()
            ax4.grid(True, alpha=0.3)

        # 5. Net grid usage (import - export)
        ax5 = plt.subplot(6, 2, 5)
        if 'monthly_summary' in monthly_data and 'Net_Grid_kWh' in monthly_data['monthly_summary'].columns:
            summary = monthly_data['monthly_summary']
            colors = ['red' if x > 0 else 'green' for x in summary['Net_Grid_kWh']]
            ax5.bar(summary.index.strftime('%b %Y'), summary['Net_Grid_kWh'], color=colors, alpha=0.7)
            ax5.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax5.set_xlabel('Month')
            ax5.set_ylabel('Net Grid Usage (kWh)')
            ax5.set_title('Net Grid Usage by Month (Red=Import, Green=Export)', fontsize=14, fontweight='bold')
            ax5.tick_params(axis='x', rotation=45)
            ax5.grid(True, alpha=0.3)

        # 6. Heatmap of hourly usage by day of week
        ax6 = plt.subplot(6, 2, 6)
        if hourly_data and 'df_hourly' in hourly_data:
            df_hourly = hourly_data['df_hourly']
            if 'Grid' in df_hourly.columns:
                pivot = df_hourly.pivot_table(values='Grid', index='day_of_week', columns='hour', aggfunc='mean')
                sns.heatmap(pivot, cmap='YlOrRd', ax=ax6, cbar_kws={'label': 'Grid Import (kW)'})
                ax6.set_yticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
                ax6.set_xlabel('Hour of Day')
                ax6.set_ylabel('Day of Week')
                ax6.set_title('Grid Usage Heatmap by Hour and Day', fontsize=14, fontweight='bold')

        # 7. Solar production vs consumption scatter
        ax7 = plt.subplot(6, 2, 7)
        if 'Solar' in df.columns and 'Grid' in df.columns:
            # Sample data to avoid too many points
            sample_df = df.sample(min(1000, len(df)))
            ax7.scatter(sample_df['Solar'], sample_df['Grid'], alpha=0.5, s=10)
            ax7.set_xlabel('Solar Production (kW)')
            ax7.set_ylabel('Grid Import (kW)')
            ax7.set_title('Solar Production vs Grid Import Correlation', fontsize=14, fontweight='bold')
            ax7.grid(True, alpha=0.3)

        # 8. Monthly solar efficiency
        ax8 = plt.subplot(6, 2, 8)
        if 'monthly_summary' in monthly_data and not monthly_data['monthly_summary'].empty:
            summary = monthly_data['monthly_summary']
            if 'Solar_Production_kWh' in summary.columns and 'Grid_Export_kWh' in summary.columns:
                summary['Solar_Self_Consumption'] = summary['Solar_Production_kWh'] - summary['Grid_Export_kWh']
                summary['Self_Consumption_Rate'] = (summary['Solar_Self_Consumption'] / summary['Solar_Production_kWh'] * 100).fillna(0)

                ax8.bar(summary.index.strftime('%b %Y'), summary['Self_Consumption_Rate'], color='orange', alpha=0.7)
                ax8.set_xlabel('Month')
                ax8.set_ylabel('Self Consumption Rate (%)')
                ax8.set_title('Solar Self-Consumption Rate by Month', fontsize=14, fontweight='bold')
                ax8.tick_params(axis='x', rotation=45)
                ax8.grid(True, alpha=0.3)

        # 9. Daily energy balance
        ax9 = plt.subplot(6, 2, 9)
        daily_df = df.resample('D').sum()
        if 'Grid' in daily_df.columns and 'Solar' in daily_df.columns:
            ax9.fill_between(daily_df.index, daily_df['Solar'], alpha=0.5, label='Solar Production', color='gold')
            ax9.fill_between(daily_df.index, -daily_df['Grid'], alpha=0.5, label='Grid Import', color='red')
            ax9.axhline(y=0, color='black', linestyle='-', linewidth=1)
            ax9.set_xlabel('Date')
            ax9.set_ylabel('Daily Energy (kWh)')
            ax9.set_title('Daily Energy Balance', fontsize=14, fontweight='bold')
            ax9.legend()
            ax9.grid(True, alpha=0.3)

        # 10. Peak demand analysis
        ax10 = plt.subplot(6, 2, 10)
        if 'Grid' in df.columns:
            monthly_peak = df['Grid'].resample('M').max()
            ax10.bar(monthly_peak.index.strftime('%b %Y'), monthly_peak, color='darkred', alpha=0.7)
            ax10.set_xlabel('Month')
            ax10.set_ylabel('Peak Demand (kW)')
            ax10.set_title('Monthly Peak Grid Demand', fontsize=14, fontweight='bold')
            ax10.tick_params(axis='x', rotation=45)
            ax10.grid(True, alpha=0.3)

        # 11. Cumulative energy over time
        ax11 = plt.subplot(6, 2, 11)
        if 'Grid' in df.columns and 'Solar' in df.columns:
            cumulative_grid = df['Grid'].cumsum() / 1000  # Convert to MWh
            cumulative_solar = df['Solar'].cumsum() / 1000
            ax11.plot(df.index, cumulative_grid, label='Cumulative Grid Import', linewidth=2)
            ax11.plot(df.index, cumulative_solar, label='Cumulative Solar Production', linewidth=2)
            ax11.set_xlabel('Date')
            ax11.set_ylabel('Cumulative Energy (MWh)')
            ax11.set_title('Cumulative Energy Over Time', fontsize=14, fontweight='bold')
            ax11.legend()
            ax11.grid(True, alpha=0.3)

        # 12. Cost analysis (if cost data available)
        ax12 = plt.subplot(6, 2, 12)
        if 'monthly_summary' in monthly_data and not monthly_data['monthly_summary'].empty:
            summary = monthly_data['monthly_summary']
            if 'Grid_Import_kWh' in summary.columns and 'Grid_Export_kWh' in summary.columns:
                # Assuming rates (you can adjust these)
                import_rate = 0.15  # $/kWh
                export_rate = 0.08  # $/kWh

                summary['Import_Cost'] = summary['Grid_Import_kWh'] * import_rate
                summary['Export_Revenue'] = summary['Grid_Export_kWh'] * export_rate
                summary['Net_Cost'] = summary['Import_Cost'] - summary['Export_Revenue']

                months = summary.index.strftime('%b %Y')
                x = np.arange(len(months))
                width = 0.35

                ax12.bar(x - width/2, summary['Import_Cost'], width, label='Import Cost', color='red', alpha=0.7)
                ax12.bar(x + width/2, -summary['Export_Revenue'], width, label='Export Revenue', color='green', alpha=0.7)

                ax12.set_xlabel('Month')
                ax12.set_ylabel('Cost ($)')
                ax12.set_title('Estimated Monthly Energy Costs', fontsize=14, fontweight='bold')
                ax12.set_xticks(x)
                ax12.set_xticklabels(months, rotation=45, ha='right')
                ax12.legend()
                ax12.grid(True, alpha=0.3)

        plt.suptitle('eGauge Power Monitor Analysis Dashboard', fontsize=16, fontweight='bold', y=0.995)
        plt.tight_layout()

        # Save the figure
        filename = f'egauge_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"Visualizations saved to {filename}")

        return fig

    def generate_report(self, df: pd.DataFrame, monthly_data: Dict, hourly_data: Dict):
        """
        Generate a text report with key insights
        """
        print("\n" + "="*60)
        print("eGAUGE POWER MONITOR ANALYSIS REPORT")
        print("="*60)
        print(f"Analysis Period: {df.index.min()} to {df.index.max()}")
        print(f"Total Data Points: {len(df)}")

        if 'monthly_summary' in monthly_data and not monthly_data['monthly_summary'].empty:
            summary = monthly_data['monthly_summary']

            print("\n" + "-"*40)
            print("MONTHLY SUMMARY STATISTICS")
            print("-"*40)

            if 'Grid_Import_kWh' in summary.columns:
                print(f"Average Monthly Grid Import: {summary['Grid_Import_kWh'].mean():.1f} kWh")
                print(f"Total Grid Import: {summary['Grid_Import_kWh'].sum():.1f} kWh")
                print(f"Peak Monthly Import: {summary['Grid_Import_kWh'].max():.1f} kWh in {summary['Grid_Import_kWh'].idxmax().strftime('%B %Y')}")
                print(f"Lowest Monthly Import: {summary['Grid_Import_kWh'].min():.1f} kWh in {summary['Grid_Import_kWh'].idxmin().strftime('%B %Y')}")

            if 'Solar_Production_kWh' in summary.columns:
                print(f"\nAverage Monthly Solar Production: {summary['Solar_Production_kWh'].mean():.1f} kWh")
                print(f"Total Solar Production: {summary['Solar_Production_kWh'].sum():.1f} kWh")
                print(f"Peak Monthly Production: {summary['Solar_Production_kWh'].max():.1f} kWh in {summary['Solar_Production_kWh'].idxmax().strftime('%B %Y')}")
                print(f"Lowest Monthly Production: {summary['Solar_Production_kWh'].min():.1f} kWh in {summary['Solar_Production_kWh'].idxmin().strftime('%B %Y')}")

            if 'Grid_Export_kWh' in summary.columns:
                print(f"\nTotal Grid Export: {summary['Grid_Export_kWh'].sum():.1f} kWh")
                print(f"Average Monthly Export: {summary['Grid_Export_kWh'].mean():.1f} kWh")

            if 'Net_Grid_kWh' in summary.columns:
                net_import_months = (summary['Net_Grid_kWh'] > 0).sum()
                net_export_months = (summary['Net_Grid_kWh'] < 0).sum()
                print(f"\nNet Importing Months: {net_import_months}")
                print(f"Net Exporting Months: {net_export_months}")

        if hourly_data and 'hourly_avg' in hourly_data:
            hourly_avg = hourly_data['hourly_avg']

            print("\n" + "-"*40)
            print("HOURLY USAGE PATTERNS")
            print("-"*40)

            if 'Grid' in hourly_avg.columns:
                peak_hour = hourly_avg['Grid'].idxmax()
                low_hour = hourly_avg['Grid'].idxmin()
                print(f"Peak Usage Hour: {peak_hour}:00 ({hourly_avg['Grid'][peak_hour]:.2f} kW average)")
                print(f"Lowest Usage Hour: {low_hour}:00 ({hourly_avg['Grid'][low_hour]:.2f} kW average)")

            if 'Solar' in hourly_avg.columns:
                peak_solar = hourly_avg['Solar'].idxmax()
                print(f"Peak Solar Hour: {peak_solar}:00 ({hourly_avg['Solar'][peak_solar]:.2f} kW average)")

        # Calculate some key metrics
        if 'Grid' in df.columns:
            print("\n" + "-"*40)
            print("KEY PERFORMANCE METRICS")
            print("-"*40)

            peak_demand = df['Grid'].max()
            avg_demand = df['Grid'].mean()
            print(f"Peak Demand: {peak_demand:.2f} kW")
            print(f"Average Demand: {avg_demand:.2f} kW")
            print(f"Load Factor: {(avg_demand/peak_demand*100):.1f}%")

        if 'Solar' in df.columns and 'Grid' in df.columns:
            # Calculate solar offset
            total_consumption = df['Grid'].sum()
            total_solar = df['Solar'].sum()
            solar_offset = (total_solar / (total_consumption + total_solar) * 100) if (total_consumption + total_solar) > 0 else 0
            print(f"Solar Offset: {solar_offset:.1f}% of total consumption")

        print("\n" + "="*60)


def main():
    """
    Main function to run the analysis
    """
    print("Starting eGauge Power Monitor Analysis")
    print("="*60)

    # Initialize analyzer
    analyzer = EGaugeAnalyzer(EGAUGE_IP)

    # Fetch historical data (1 year)
    df = analyzer.fetch_historical_data(days_back=365)

    if df.empty:
        print("No data available. Please check your eGauge connection.")
        return

    # Analyze monthly patterns
    monthly_data = analyzer.analyze_monthly_patterns(df)

    # Analyze hourly patterns
    hourly_data = analyzer.analyze_hourly_patterns(df)

    # Generate visualizations
    fig = analyzer.create_visualizations(df, monthly_data, hourly_data)

    # Generate report
    analyzer.generate_report(df, monthly_data, hourly_data)

    # Show the plot
    plt.show()

    print("\nAnalysis complete!")


if __name__ == "__main__":
    main()