#!/usr/bin/env python3
"""
eGauge Power Monitor Comprehensive Analysis
Analyzes power consumption and solar production data
"""

import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# Configuration
EGAUGE_IP = "10.10.20.241"

# Set style for better-looking plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

class EGaugeDataCollector:
    def __init__(self, ip_address: str):
        self.ip = ip_address
        self.base_url = f"http://{ip_address}"

    def fetch_monthly_data(self) -> pd.DataFrame:
        """Fetch monthly data for the past year"""
        print("Fetching monthly data for the past year...")
        url = f"{self.base_url}/cgi-bin/egauge-show?m&n=12"

        try:
            response = requests.get(url, timeout=10)
            root = ET.fromstring(response.content)

            data_points = []
            for group in root.findall('.//group'):
                timestamp_elem = group.find('timestamp')
                if timestamp_elem is not None:
                    ts = int(timestamp_elem.text)
                    dt = datetime.fromtimestamp(ts)

                    row_data = {'timestamp': dt}

                    for data in group.findall('data'):
                        cname = data.find('cname').text if data.find('cname') is not None else None
                        if cname:
                            columns = data.findall('.//column')
                            if columns:
                                # Get the delta value (monthly change)
                                for col in columns:
                                    if col.text:
                                        try:
                                            value = float(col.text) / 1000.0  # Convert to kWh
                                            row_data[cname] = value
                                        except:
                                            pass

                    if row_data:
                        data_points.append(row_data)

            if data_points:
                df = pd.DataFrame(data_points)
                df = df.set_index('timestamp')
                df = df.sort_index()
                print(f"Fetched {len(df)} monthly data points")
                return df

        except Exception as e:
            print(f"Error fetching monthly data: {e}")

        return pd.DataFrame()

    def fetch_daily_data(self, days: int = 30) -> pd.DataFrame:
        """Fetch daily data"""
        print(f"Fetching {days} days of daily data...")
        url = f"{self.base_url}/cgi-bin/egauge-show?d&n={days}"

        try:
            response = requests.get(url, timeout=10)
            root = ET.fromstring(response.content)

            data_points = []
            for group in root.findall('.//group'):
                timestamp_elem = group.find('timestamp')
                if timestamp_elem is not None:
                    ts = int(timestamp_elem.text)
                    dt = datetime.fromtimestamp(ts)

                    row_data = {'timestamp': dt}

                    for data in group.findall('data'):
                        cname = data.find('cname').text if data.find('cname') is not None else None
                        if cname:
                            columns = data.findall('.//column')
                            if columns:
                                for col in columns:
                                    if col.text:
                                        try:
                                            value = float(col.text) / 1000.0  # Convert to kWh
                                            row_data[cname] = value
                                        except:
                                            pass

                    if row_data:
                        data_points.append(row_data)

            if data_points:
                df = pd.DataFrame(data_points)
                df = df.set_index('timestamp')
                df = df.sort_index()
                print(f"Fetched {len(df)} daily data points")
                return df

        except Exception as e:
            print(f"Error fetching daily data: {e}")

        return pd.DataFrame()

    def fetch_hourly_data(self, hours: int = 168) -> pd.DataFrame:
        """Fetch hourly data (default: 1 week)"""
        print(f"Fetching {hours} hours of hourly data...")
        url = f"{self.base_url}/cgi-bin/egauge-show?h&n={hours}"

        try:
            response = requests.get(url, timeout=10)
            root = ET.fromstring(response.content)

            data_points = []
            for group in root.findall('.//group'):
                timestamp_elem = group.find('timestamp')
                if timestamp_elem is not None:
                    ts = int(timestamp_elem.text)
                    dt = datetime.fromtimestamp(ts)

                    row_data = {'timestamp': dt}

                    for data in group.findall('data'):
                        cname = data.find('cname').text if data.find('cname') is not None else None
                        if cname:
                            columns = data.findall('.//column')
                            if columns:
                                for col in columns:
                                    if col.text:
                                        try:
                                            value = float(col.text)  # Keep in Wh for hourly
                                            row_data[cname] = value
                                        except:
                                            pass

                    if row_data:
                        data_points.append(row_data)

            if data_points:
                df = pd.DataFrame(data_points)
                df = df.set_index('timestamp')
                df = df.sort_index()

                # Calculate hourly changes (delta values)
                for col in df.columns:
                    df[f'{col}_delta'] = df[col].diff()

                print(f"Fetched {len(df)} hourly data points")
                return df

        except Exception as e:
            print(f"Error fetching hourly data: {e}")

        return pd.DataFrame()

    def get_current_readings(self) -> dict:
        """Get current power readings"""
        url = f"{self.base_url}/cgi-bin/egauge?inst"
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                root = ET.fromstring(response.content)
                readings = {}
                for reg in root.findall('.//r'):
                    name = reg.get('n')
                    power_element = reg.find('i')
                    if power_element is not None:
                        power = float(power_element.text) / 1000.0  # Convert to kW
                        readings[name] = power
                return readings
        except Exception as e:
            print(f"Error getting current readings: {e}")
        return {}


class EGaugeAnalyzer:
    def __init__(self, collector: EGaugeDataCollector):
        self.collector = collector

    def analyze_all_data(self):
        """Perform comprehensive analysis"""
        print("\n" + "="*60)
        print("eGAUGE COMPREHENSIVE POWER ANALYSIS")
        print("="*60)

        # Get current readings
        current = self.collector.get_current_readings()
        if current:
            print("\nCURRENT POWER READINGS:")
            print("-"*40)
            print(f"Grid Power: {current.get('Grid', 0):.2f} kW")
            print(f"Solar Production: {current.get('Solar', 0):.2f} kW")
            print(f"Grid Export: {current.get('Grid_Outgoing', 0):.2f} kW")
            print(f"Grid Import: {current.get('Grid_Incoming', 0):.2f} kW")

        # Fetch all data types
        monthly_df = self.collector.fetch_monthly_data()
        daily_df = self.collector.fetch_daily_data(365)  # Get full year of daily data
        hourly_df = self.collector.fetch_hourly_data(24*7)  # Get 1 week of hourly data

        # Create visualizations
        self.create_comprehensive_plots(monthly_df, daily_df, hourly_df, current)

        # Generate report
        self.generate_detailed_report(monthly_df, daily_df, hourly_df)

    def create_comprehensive_plots(self, monthly_df, daily_df, hourly_df, current):
        """Create comprehensive visualization dashboard"""
        fig = plt.figure(figsize=(24, 20))
        fig.suptitle('eGauge Power Monitor Analysis Dashboard', fontsize=18, fontweight='bold')

        # 1. Monthly Energy Balance
        ax1 = plt.subplot(4, 3, 1)
        if not monthly_df.empty:
            months = monthly_df.index.strftime('%b\n%Y')

            # Calculate monthly deltas (changes)
            grid_import = monthly_df.get('Grid', pd.Series()).abs()
            solar_prod = monthly_df.get('Solar', pd.Series()).abs()

            x = np.arange(len(months))
            width = 0.35

            if not grid_import.empty:
                ax1.bar(x - width/2, grid_import, width, label='Grid Import', color='#FF6B6B', alpha=0.8)
            if not solar_prod.empty:
                ax1.bar(x + width/2, solar_prod, width, label='Solar Production', color='#51CF66', alpha=0.8)

            ax1.set_xlabel('Month')
            ax1.set_ylabel('Energy (kWh)')
            ax1.set_title('Monthly Energy Summary', fontweight='bold')
            ax1.set_xticks(x)
            ax1.set_xticklabels(months, rotation=0, ha='center')
            ax1.legend()
            ax1.grid(True, alpha=0.3)

        # 2. Daily Pattern for Last 30 Days
        ax2 = plt.subplot(4, 3, 2)
        if not daily_df.empty and len(daily_df) > 0:
            recent_daily = daily_df.tail(30)
            if 'Grid' in recent_daily.columns:
                ax2.bar(recent_daily.index, recent_daily['Grid'].abs(),
                       color='#FF6B6B', alpha=0.6, label='Grid')
            if 'Solar' in recent_daily.columns:
                ax2.bar(recent_daily.index, -recent_daily['Solar'].abs(),
                       color='#51CF66', alpha=0.6, label='Solar')

            ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
            ax2.set_xlabel('Date')
            ax2.set_ylabel('Daily Energy (kWh)')
            ax2.set_title('Last 30 Days Energy Flow', fontweight='bold')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

        # 3. Hourly Pattern Analysis
        ax3 = plt.subplot(4, 3, 3)
        if not hourly_df.empty:
            # Group by hour of day
            hourly_df['hour'] = hourly_df.index.hour

            # Use delta columns if available
            grid_col = 'Grid_delta' if 'Grid_delta' in hourly_df.columns else 'Grid'
            solar_col = 'Solar_delta' if 'Solar_delta' in hourly_df.columns else 'Solar'

            hourly_avg = hourly_df.groupby('hour').mean()

            if grid_col in hourly_avg.columns:
                ax3.plot(hourly_avg.index, hourly_avg[grid_col].abs()/1000,
                        marker='o', linewidth=2, label='Grid', color='#FF6B6B')
            if solar_col in hourly_avg.columns:
                ax3.plot(hourly_avg.index, hourly_avg[solar_col].abs()/1000,
                        marker='s', linewidth=2, label='Solar', color='#51CF66')

            ax3.set_xlabel('Hour of Day')
            ax3.set_ylabel('Average Power (kW)')
            ax3.set_title('Average Hourly Power Pattern', fontweight='bold')
            ax3.set_xticks(range(0, 24, 2))
            ax3.legend()
            ax3.grid(True, alpha=0.3)

        # 4. Year Overview - Daily
        ax4 = plt.subplot(4, 3, 4)
        if not daily_df.empty and len(daily_df) > 30:
            if 'Grid' in daily_df.columns and 'Solar' in daily_df.columns:
                ax4.fill_between(daily_df.index, daily_df['Solar'].abs(),
                                alpha=0.5, label='Solar', color='#51CF66')
                ax4.fill_between(daily_df.index, -daily_df['Grid'].abs(),
                                alpha=0.5, label='Grid', color='#FF6B6B')
                ax4.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
                ax4.set_xlabel('Date')
                ax4.set_ylabel('Daily Energy (kWh)')
                ax4.set_title('Year Overview - Energy Balance', fontweight='bold')
                ax4.legend()
                ax4.grid(True, alpha=0.3)

        # 5. Monthly Comparison Chart
        ax5 = plt.subplot(4, 3, 5)
        if not monthly_df.empty and len(monthly_df) > 1:
            # Calculate net energy for each month
            if 'Grid' in monthly_df.columns and 'Solar' in monthly_df.columns:
                net_energy = monthly_df['Solar'].abs() - monthly_df['Grid'].abs()
                colors = ['#51CF66' if x > 0 else '#FF6B6B' for x in net_energy]

                ax5.bar(monthly_df.index.strftime('%b'), net_energy, color=colors, alpha=0.7)
                ax5.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
                ax5.set_xlabel('Month')
                ax5.set_ylabel('Net Energy (kWh)')
                ax5.set_title('Monthly Net Energy (Green=Export, Red=Import)', fontweight='bold')
                ax5.grid(True, alpha=0.3)
                plt.setp(ax5.xaxis.get_majorticklabels(), rotation=45)

        # 6. Solar Production Efficiency
        ax6 = plt.subplot(4, 3, 6)
        if not daily_df.empty and 'Solar' in daily_df.columns:
            # Group by month
            daily_df['month'] = daily_df.index.month
            monthly_solar = daily_df.groupby('month')['Solar'].agg(['mean', 'max', 'min']).abs()

            months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                     'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

            x = list(monthly_solar.index)
            ax6.fill_between(x, monthly_solar['min'], monthly_solar['max'],
                            alpha=0.3, color='#51CF66', label='Min-Max Range')
            ax6.plot(x, monthly_solar['mean'], marker='o', linewidth=2,
                    color='#2E8B57', label='Average')

            ax6.set_xlabel('Month')
            ax6.set_ylabel('Solar Production (kWh/day)')
            ax6.set_title('Solar Production by Month', fontweight='bold')
            ax6.set_xticks(range(1, 13))
            ax6.set_xticklabels([months[i-1] for i in range(1, len(x)+1)])
            ax6.legend()
            ax6.grid(True, alpha=0.3)

        # 7. Weekly Pattern Heatmap
        ax7 = plt.subplot(4, 3, 7)
        if not hourly_df.empty and len(hourly_df) > 24:
            hourly_df['hour'] = hourly_df.index.hour
            hourly_df['day'] = hourly_df.index.dayofweek

            grid_col = 'Grid_delta' if 'Grid_delta' in hourly_df.columns else 'Grid'
            if grid_col in hourly_df.columns:
                pivot = hourly_df.pivot_table(values=grid_col, index='day',
                                             columns='hour', aggfunc='mean')
                pivot = pivot.abs() / 1000  # Convert to kW

                sns.heatmap(pivot, cmap='YlOrRd', ax=ax7,
                          cbar_kws={'label': 'Grid Usage (kW)'})
                ax7.set_yticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
                ax7.set_xlabel('Hour of Day')
                ax7.set_ylabel('Day of Week')
                ax7.set_title('Weekly Grid Usage Pattern', fontweight='bold')

        # 8. Cost Analysis
        ax8 = plt.subplot(4, 3, 8)
        if not monthly_df.empty:
            # Estimate costs (adjust rates as needed)
            import_rate = 0.15  # $/kWh
            export_rate = 0.08  # $/kWh

            if 'Grid' in monthly_df.columns:
                import_cost = monthly_df['Grid'].abs() * import_rate

                # Estimate export from solar excess
                if 'Solar' in monthly_df.columns:
                    export_revenue = (monthly_df['Solar'].abs() * 0.3) * export_rate  # Assume 30% export
                    net_cost = import_cost - export_revenue

                    months = monthly_df.index.strftime('%b')
                    x = np.arange(len(months))
                    width = 0.35

                    ax8.bar(x - width/2, import_cost, width, label='Import Cost',
                           color='#FF6B6B', alpha=0.8)
                    ax8.bar(x + width/2, -export_revenue, width, label='Export Revenue',
                           color='#51CF66', alpha=0.8)

                    ax8.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
                    ax8.set_xlabel('Month')
                    ax8.set_ylabel('Cost ($)')
                    ax8.set_title('Estimated Monthly Energy Costs', fontweight='bold')
                    ax8.set_xticks(x)
                    ax8.set_xticklabels(months, rotation=45)
                    ax8.legend()
                    ax8.grid(True, alpha=0.3)

        # 9. Current Status Gauge
        ax9 = plt.subplot(4, 3, 9)
        if current:
            # Create a simple gauge visualization
            grid_power = current.get('Grid', 0)
            solar_power = current.get('Solar', 0)

            categories = ['Grid', 'Solar', 'Export', 'Import']
            values = [
                abs(grid_power),
                abs(solar_power),
                abs(current.get('Grid_Outgoing', 0)),
                abs(current.get('Grid_Incoming', 0))
            ]
            colors_gauge = ['#FF6B6B', '#51CF66', '#4ECDC4', '#F7B731']

            ax9.barh(categories, values, color=colors_gauge, alpha=0.8)
            ax9.set_xlabel('Power (kW)')
            ax9.set_title(f'Current Power Status ({datetime.now().strftime("%H:%M")})',
                         fontweight='bold')
            ax9.grid(True, alpha=0.3, axis='x')

        # 10. Peak Demand Analysis
        ax10 = plt.subplot(4, 3, 10)
        if not daily_df.empty and 'Grid' in daily_df.columns:
            # Group by month and find peak days
            daily_df['month'] = daily_df.index.to_period('M')
            monthly_peaks = daily_df.groupby('month')['Grid'].max().abs()

            if len(monthly_peaks) > 0:
                ax10.bar(range(len(monthly_peaks)), monthly_peaks.values,
                        color='#FF6B6B', alpha=0.8)
                ax10.set_xlabel('Month')
                ax10.set_ylabel('Peak Daily Demand (kWh)')
                ax10.set_title('Monthly Peak Demand Days', fontweight='bold')
                ax10.set_xticks(range(len(monthly_peaks)))
                ax10.set_xticklabels([str(m) for m in monthly_peaks.index], rotation=45)
                ax10.grid(True, alpha=0.3)

        # 11. Solar vs Grid Correlation
        ax11 = plt.subplot(4, 3, 11)
        if not daily_df.empty and 'Grid' in daily_df.columns and 'Solar' in daily_df.columns:
            # Scatter plot of solar vs grid
            ax11.scatter(daily_df['Solar'].abs(), daily_df['Grid'].abs(),
                        alpha=0.5, s=20, color='#8B4789')

            # Add trend line
            z = np.polyfit(daily_df['Solar'].abs().fillna(0),
                          daily_df['Grid'].abs().fillna(0), 1)
            p = np.poly1d(z)
            x_trend = np.linspace(daily_df['Solar'].abs().min(),
                                 daily_df['Solar'].abs().max(), 100)
            ax11.plot(x_trend, p(x_trend), "r--", alpha=0.8, label='Trend')

            ax11.set_xlabel('Solar Production (kWh/day)')
            ax11.set_ylabel('Grid Import (kWh/day)')
            ax11.set_title('Solar Production vs Grid Import', fontweight='bold')
            ax11.legend()
            ax11.grid(True, alpha=0.3)

        # 12. Summary Statistics Box
        ax12 = plt.subplot(4, 3, 12)
        ax12.axis('off')

        # Calculate summary statistics
        summary_text = "SUMMARY STATISTICS\n" + "="*30 + "\n\n"

        if not monthly_df.empty:
            if 'Grid' in monthly_df.columns:
                total_grid = monthly_df['Grid'].abs().sum()
                avg_grid = monthly_df['Grid'].abs().mean()
                summary_text += f"Total Grid Import: {total_grid:,.0f} kWh\n"
                summary_text += f"Avg Monthly Grid: {avg_grid:,.0f} kWh\n\n"

            if 'Solar' in monthly_df.columns:
                total_solar = monthly_df['Solar'].abs().sum()
                avg_solar = monthly_df['Solar'].abs().mean()
                summary_text += f"Total Solar Prod: {total_solar:,.0f} kWh\n"
                summary_text += f"Avg Monthly Solar: {avg_solar:,.0f} kWh\n\n"

        if not daily_df.empty:
            if 'Grid' in daily_df.columns:
                peak_day = daily_df['Grid'].abs().max()
                avg_daily = daily_df['Grid'].abs().mean()
                summary_text += f"Peak Day Demand: {peak_day:,.0f} kWh\n"
                summary_text += f"Avg Daily Demand: {avg_daily:,.0f} kWh\n\n"

        # Add cost estimates
        if not monthly_df.empty and 'Grid' in monthly_df.columns:
            annual_cost = monthly_df['Grid'].abs().sum() * 0.15
            if 'Solar' in monthly_df.columns:
                annual_savings = monthly_df['Solar'].abs().sum() * 0.15
                summary_text += f"Est Annual Cost: ${annual_cost:,.0f}\n"
                summary_text += f"Est Solar Savings: ${annual_savings:,.0f}\n"
                summary_text += f"Net Savings: ${(annual_savings-annual_cost):,.0f}\n"

        ax12.text(0.1, 0.9, summary_text, transform=ax12.transAxes,
                 fontsize=11, verticalalignment='top',
                 fontfamily='monospace',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

        plt.tight_layout()

        # Save the figure
        filename = f'egauge_analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"\nVisualizations saved to {filename}")

        plt.show()

    def generate_detailed_report(self, monthly_df, daily_df, hourly_df):
        """Generate detailed text report"""
        print("\n" + "="*60)
        print("DETAILED ANALYSIS REPORT")
        print("="*60)

        # Monthly Analysis
        if not monthly_df.empty:
            print("\nMONTHLY ANALYSIS")
            print("-"*40)

            if 'Grid' in monthly_df.columns:
                grid_data = monthly_df['Grid'].abs()
                print(f"Grid Import Statistics:")
                print(f"  Total: {grid_data.sum():,.0f} kWh")
                print(f"  Monthly Average: {grid_data.mean():,.0f} kWh")
                print(f"  Peak Month: {grid_data.max():,.0f} kWh ({grid_data.idxmax().strftime('%B %Y')})")
                print(f"  Lowest Month: {grid_data.min():,.0f} kWh ({grid_data.idxmin().strftime('%B %Y')})")

            if 'Solar' in monthly_df.columns:
                solar_data = monthly_df['Solar'].abs()
                print(f"\nSolar Production Statistics:")
                print(f"  Total: {solar_data.sum():,.0f} kWh")
                print(f"  Monthly Average: {solar_data.mean():,.0f} kWh")
                print(f"  Peak Month: {solar_data.max():,.0f} kWh ({solar_data.idxmax().strftime('%B %Y')})")
                print(f"  Lowest Month: {solar_data.min():,.0f} kWh ({solar_data.idxmin().strftime('%B %Y')})")

        # Daily Analysis
        if not daily_df.empty:
            print("\nDAILY PATTERNS")
            print("-"*40)

            if 'Grid' in daily_df.columns:
                grid_daily = daily_df['Grid'].abs()
                print(f"Daily Grid Usage:")
                print(f"  Average: {grid_daily.mean():,.1f} kWh/day")
                print(f"  Peak Day: {grid_daily.max():,.1f} kWh")
                print(f"  Minimum Day: {grid_daily.min():,.1f} kWh")

            if 'Solar' in daily_df.columns:
                solar_daily = daily_df['Solar'].abs()
                print(f"\nDaily Solar Production:")
                print(f"  Average: {solar_daily.mean():,.1f} kWh/day")
                print(f"  Peak Day: {solar_daily.max():,.1f} kWh")
                print(f"  Minimum Day: {solar_daily.min():,.1f} kWh")

        # Hourly Analysis
        if not hourly_df.empty:
            print("\nHOURLY PATTERNS")
            print("-"*40)

            hourly_df['hour'] = hourly_df.index.hour
            grid_col = 'Grid_delta' if 'Grid_delta' in hourly_df.columns else 'Grid'
            solar_col = 'Solar_delta' if 'Solar_delta' in hourly_df.columns else 'Solar'

            if grid_col in hourly_df.columns:
                hourly_grid = hourly_df.groupby('hour')[grid_col].mean().abs() / 1000  # Convert to kW
                peak_hour = hourly_grid.idxmax()
                print(f"Peak Grid Usage Hour: {peak_hour}:00 ({hourly_grid[peak_hour]:.2f} kW average)")
                print(f"Lowest Usage Hour: {hourly_grid.idxmin()}:00 ({hourly_grid.min():.2f} kW average)")

            if solar_col in hourly_df.columns:
                hourly_solar = hourly_df.groupby('hour')[solar_col].mean().abs() / 1000
                peak_solar = hourly_solar.idxmax()
                print(f"\nPeak Solar Hour: {peak_solar}:00 ({hourly_solar[peak_solar]:.2f} kW average)")

        # Financial Analysis
        print("\nFINANCIAL ANALYSIS (Estimated)")
        print("-"*40)

        if not monthly_df.empty and 'Grid' in monthly_df.columns:
            import_rate = 0.15  # $/kWh
            total_grid = monthly_df['Grid'].abs().sum()
            annual_grid_cost = total_grid * import_rate

            print(f"Annual Grid Import Cost: ${annual_grid_cost:,.2f}")

            if 'Solar' in monthly_df.columns:
                total_solar = monthly_df['Solar'].abs().sum()
                solar_value = total_solar * import_rate  # Value of solar at grid rate
                export_rate = 0.08  # $/kWh for exports
                export_revenue = total_solar * 0.3 * export_rate  # Assume 30% exported

                print(f"Solar Production Value: ${solar_value:,.2f}")
                print(f"Estimated Export Revenue: ${export_revenue:,.2f}")
                print(f"Net Annual Savings: ${(solar_value - annual_grid_cost + export_revenue):,.2f}")

        print("\n" + "="*60)


def main():
    """Main function"""
    collector = EGaugeDataCollector(EGAUGE_IP)
    analyzer = EGaugeAnalyzer(collector)
    analyzer.analyze_all_data()


if __name__ == "__main__":
    main()