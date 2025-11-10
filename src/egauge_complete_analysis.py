#!/usr/bin/env python3
"""
eGauge Power Monitor Complete Analysis
Comprehensive analysis with proper data parsing
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.gridspec import GridSpec
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

# Configuration
EGAUGE_IP = "10.10.20.241"

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

class EGaugeDataParser:
    def __init__(self, ip_address: str):
        self.ip = ip_address
        self.base_url = f"http://{ip_address}/cgi-bin"

    def parse_cumulative_data(self, xml_string: str, interval: str = 'hourly') -> pd.DataFrame:
        """Parse cumulative energy data from eGauge XML"""
        try:
            root = ET.fromstring(xml_string)

            # Get column names
            columns = {}
            for cname in root.findall('.//cname'):
                did = cname.get('did')
                name = cname.text
                columns[int(did)] = name

            # Get time info
            data_elem = root.find('.//data')
            if data_elem is None:
                return pd.DataFrame()

            time_stamp = int(data_elem.get('time_stamp'), 16)
            time_delta = int(data_elem.get('time_delta'))

            # Parse data rows
            rows = []
            current_time = datetime.fromtimestamp(time_stamp)

            for r in root.findall('.//r'):
                row_data = {'timestamp': current_time}

                for i, c in enumerate(r.findall('c')):
                    if i in columns:
                        # Store cumulative value in Wh
                        value = float(c.text) if c.text else 0
                        row_data[columns[i]] = value

                rows.append(row_data)
                current_time = current_time - timedelta(seconds=time_delta)

            df = pd.DataFrame(rows)
            if not df.empty:
                df = df.set_index('timestamp')
                df = df.sort_index()

                # Calculate differences (actual consumption/production)
                for col in df.columns:
                    df[f'{col}_delta'] = -df[col].diff(-1)  # Negative diff for forward calculation

                # Convert delta values to kWh based on interval
                if interval == 'monthly':
                    # Monthly data - values are already in Wh, convert to kWh
                    for col in df.columns:
                        if '_delta' in col:
                            df[col] = df[col] / 1000.0
                elif interval == 'daily':
                    # Daily data - convert Wh to kWh
                    for col in df.columns:
                        if '_delta' in col:
                            df[col] = df[col] / 1000.0
                elif interval == 'hourly':
                    # Hourly data - convert Wh to kW (power)
                    for col in df.columns:
                        if '_delta' in col:
                            df[col] = df[col] / 1000.0  # Convert to kW

            return df

        except Exception as e:
            print(f"Error parsing data: {e}")
            return pd.DataFrame()

    def fetch_data(self, period: str, count: int) -> pd.DataFrame:
        """Fetch and parse data for specified period"""
        url = f"{self.base_url}/egauge-show?{period}&n={count}"

        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()

            interval_map = {'m': 'monthly', 'd': 'daily', 'h': 'hourly'}
            interval = interval_map.get(period, 'hourly')

            return self.parse_cumulative_data(response.content, interval)

        except Exception as e:
            print(f"Error fetching {period} data: {e}")
            return pd.DataFrame()

    def get_current_power(self) -> dict:
        """Get current instantaneous power readings"""
        url = f"{self.base_url}/egauge?inst"
        try:
            response = requests.get(url, timeout=5)
            root = ET.fromstring(response.content)

            readings = {}
            for reg in root.findall('.//r'):
                name = reg.get('n')
                power_elem = reg.find('i')
                if power_elem is not None:
                    power = float(power_elem.text) / 1000.0  # Convert W to kW
                    readings[name] = power

            return readings
        except Exception as e:
            print(f"Error getting current readings: {e}")
            return {}


class PowerAnalysisReport:
    def __init__(self, parser: EGaugeDataParser):
        self.parser = parser

    def generate_complete_analysis(self):
        """Generate complete analysis with all visualizations"""
        print("\n" + "="*70)
        print(" "*20 + "eGAUGE POWER ANALYSIS REPORT")
        print("="*70)
        print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"eGauge Device: {self.parser.ip}")
        print("="*70)

        # Fetch all data
        print("\nFetching data from eGauge...")
        monthly_df = self.parser.fetch_data('m', 12)  # 12 months
        daily_df = self.parser.fetch_data('d', 365)   # 365 days
        hourly_df = self.parser.fetch_data('h', 24*7)  # 1 week hourly
        current = self.parser.get_current_power()

        print(f"  Monthly data points: {len(monthly_df)}")
        print(f"  Daily data points: {len(daily_df)}")
        print(f"  Hourly data points: {len(hourly_df)}")

        # Current status
        if current:
            print("\n" + "-"*50)
            print("CURRENT STATUS")
            print("-"*50)
            print(f"Grid Power:      {current.get('Grid', 0):8.2f} kW")
            print(f"Solar Production:{current.get('Solar', 0):8.2f} kW")
            print(f"Grid Export:     {current.get('Grid_Outgoing', 0):8.2f} kW")
            print(f"Grid Import:     {current.get('Grid_Incoming', 0):8.2f} kW")
            net_grid = current.get('Grid_Incoming', 0) - current.get('Grid_Outgoing', 0)
            print(f"Net Grid:        {net_grid:8.2f} kW {'(importing)' if net_grid > 0 else '(exporting)'}")

        # Generate visualizations
        self.create_comprehensive_dashboard(monthly_df, daily_df, hourly_df, current)

        # Generate statistics
        self.print_detailed_statistics(monthly_df, daily_df, hourly_df)

    def create_comprehensive_dashboard(self, monthly_df, daily_df, hourly_df, current):
        """Create comprehensive visualization dashboard"""

        # Create figure with custom layout
        fig = plt.figure(figsize=(24, 16))
        gs = GridSpec(4, 4, figure=fig, hspace=0.3, wspace=0.25)

        # Define color scheme
        grid_color = '#E74C3C'
        solar_color = '#27AE60'
        export_color = '#3498DB'
        import_color = '#E67E22'

        # 1. Monthly Energy Overview (Top row, spanning 2 columns)
        ax1 = fig.add_subplot(gs[0, :2])
        if not monthly_df.empty:
            # Use delta columns for actual monthly consumption/production
            grid_data = monthly_df.get('Grid_delta', pd.Series())
            solar_data = monthly_df.get('Solar_delta', pd.Series())

            if not grid_data.empty or not solar_data.empty:
                months = monthly_df.index.strftime('%b\n%Y')
                x = np.arange(len(months))
                width = 0.35

                if not grid_data.empty:
                    ax1.bar(x - width/2, grid_data.abs(), width,
                           label='Grid Consumption', color=grid_color, alpha=0.8)
                if not solar_data.empty:
                    ax1.bar(x + width/2, solar_data.abs(), width,
                           label='Solar Production', color=solar_color, alpha=0.8)

                ax1.set_xlabel('Month', fontsize=11)
                ax1.set_ylabel('Energy (kWh)', fontsize=11)
                ax1.set_title('Monthly Energy Overview', fontsize=14, fontweight='bold')
                ax1.set_xticks(x)
                ax1.set_xticklabels(months, fontsize=9)
                ax1.legend(loc='upper right')
                ax1.grid(True, alpha=0.3)

        # 2. Daily Pattern - Last 30 Days (Top row, spanning 2 columns)
        ax2 = fig.add_subplot(gs[0, 2:])
        if not daily_df.empty:
            recent = daily_df.head(30)  # Most recent 30 days
            if 'Grid_delta' in recent.columns and 'Solar_delta' in recent.columns:
                ax2.fill_between(recent.index, 0, recent['Solar_delta'].abs(),
                               color=solar_color, alpha=0.6, label='Solar')
                ax2.fill_between(recent.index, 0, -recent['Grid_delta'].abs(),
                               color=grid_color, alpha=0.6, label='Grid')
                ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.8)
                ax2.set_xlabel('Date', fontsize=11)
                ax2.set_ylabel('Daily Energy (kWh)', fontsize=11)
                ax2.set_title('Last 30 Days Energy Flow', fontsize=14, fontweight='bold')
                ax2.legend(loc='upper right')
                ax2.grid(True, alpha=0.3)
                ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
                plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

        # 3. Hourly Pattern
        ax3 = fig.add_subplot(gs[1, 0])
        if not hourly_df.empty:
            hourly_df['hour'] = hourly_df.index.hour
            hourly_avg = hourly_df.groupby('hour')[['Grid_delta', 'Solar_delta']].mean()

            ax3.plot(hourly_avg.index, hourly_avg['Grid_delta'].abs(),
                    marker='o', linewidth=2, label='Grid', color=grid_color)
            ax3.plot(hourly_avg.index, hourly_avg['Solar_delta'].abs(),
                    marker='s', linewidth=2, label='Solar', color=solar_color)
            ax3.set_xlabel('Hour of Day', fontsize=11)
            ax3.set_ylabel('Average Power (kW)', fontsize=11)
            ax3.set_title('Hourly Power Pattern', fontsize=12, fontweight='bold')
            ax3.set_xticks(range(0, 24, 3))
            ax3.legend()
            ax3.grid(True, alpha=0.3)

        # 4. Current Status Gauge
        ax4 = fig.add_subplot(gs[1, 1])
        if current:
            categories = ['Grid', 'Solar', 'Export', 'Import']
            values = [
                abs(current.get('Grid', 0)),
                abs(current.get('Solar', 0)),
                abs(current.get('Grid_Outgoing', 0)),
                abs(current.get('Grid_Incoming', 0))
            ]
            colors = [grid_color, solar_color, export_color, import_color]

            bars = ax4.barh(categories, values, color=colors, alpha=0.8)
            ax4.set_xlabel('Power (kW)', fontsize=11)
            ax4.set_title(f'Current Status ({datetime.now().strftime("%H:%M")})',
                         fontsize=12, fontweight='bold')
            ax4.set_xlim(0, max(values) * 1.2 if values else 5)

            # Add value labels
            for bar, value in zip(bars, values):
                ax4.text(value + max(values)*0.02, bar.get_y() + bar.get_height()/2,
                        f'{value:.2f}', va='center', fontsize=10)
            ax4.grid(True, alpha=0.3, axis='x')

        # 5. Weekly Heatmap
        ax5 = fig.add_subplot(gs[1, 2:])
        if not hourly_df.empty and len(hourly_df) > 24:
            hourly_df['hour'] = hourly_df.index.hour
            hourly_df['day'] = hourly_df.index.dayofweek

            pivot = hourly_df.pivot_table(values='Grid_delta', index='day',
                                         columns='hour', aggfunc='mean')
            pivot = pivot.abs()

            if not pivot.empty:
                sns.heatmap(pivot, cmap='YlOrRd', ax=ax5,
                          cbar_kws={'label': 'Grid Usage (kW)'}, fmt='.1f')
                ax5.set_yticklabels(['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'])
                ax5.set_xlabel('Hour of Day', fontsize=11)
                ax5.set_ylabel('Day of Week', fontsize=11)
                ax5.set_title('Weekly Grid Usage Heatmap', fontsize=12, fontweight='bold')

        # 6. Year Overview
        ax6 = fig.add_subplot(gs[2, :2])
        if not daily_df.empty and len(daily_df) > 30:
            # Resample to weekly for cleaner visualization
            weekly = daily_df[['Grid_delta', 'Solar_delta']].resample('W').sum()

            if not weekly.empty:
                ax6.plot(weekly.index, weekly['Grid_delta'].abs(),
                        label='Grid Consumption', color=grid_color, linewidth=2, alpha=0.8)
                ax6.plot(weekly.index, weekly['Solar_delta'].abs(),
                        label='Solar Production', color=solar_color, linewidth=2, alpha=0.8)
                ax6.fill_between(weekly.index, 0, weekly['Grid_delta'].abs(),
                               color=grid_color, alpha=0.2)
                ax6.fill_between(weekly.index, 0, weekly['Solar_delta'].abs(),
                               color=solar_color, alpha=0.2)
                ax6.set_xlabel('Date', fontsize=11)
                ax6.set_ylabel('Weekly Energy (kWh)', fontsize=11)
                ax6.set_title('Year Overview - Weekly Totals', fontsize=12, fontweight='bold')
                ax6.legend()
                ax6.grid(True, alpha=0.3)
                ax6.xaxis.set_major_formatter(mdates.DateFormatter('%b'))

        # 7. Monthly Net Energy
        ax7 = fig.add_subplot(gs[2, 2])
        if not monthly_df.empty:
            grid_monthly = monthly_df.get('Grid_delta', pd.Series()).abs()
            solar_monthly = monthly_df.get('Solar_delta', pd.Series()).abs()

            if not grid_monthly.empty and not solar_monthly.empty:
                net_energy = solar_monthly - grid_monthly
                colors_net = [solar_color if x > 0 else grid_color for x in net_energy]

                months_short = monthly_df.index.strftime('%b')
                ax7.bar(range(len(net_energy)), net_energy, color=colors_net, alpha=0.8)
                ax7.axhline(y=0, color='black', linestyle='-', linewidth=1)
                ax7.set_xlabel('Month', fontsize=11)
                ax7.set_ylabel('Net Energy (kWh)', fontsize=11)
                ax7.set_title('Monthly Net Energy Balance', fontsize=12, fontweight='bold')
                ax7.set_xticks(range(len(months_short)))
                ax7.set_xticklabels(months_short, rotation=45)
                ax7.grid(True, alpha=0.3)

        # 8. Cost Analysis
        ax8 = fig.add_subplot(gs[2, 3])
        if not monthly_df.empty:
            import_rate = 0.15  # $/kWh
            export_rate = 0.08  # $/kWh

            grid_monthly = monthly_df.get('Grid_delta', pd.Series()).abs()

            if not grid_monthly.empty:
                import_cost = grid_monthly * import_rate

                # Estimate export based on solar excess
                if 'Solar_delta' in monthly_df.columns:
                    solar_monthly = monthly_df['Solar_delta'].abs()
                    # Rough estimate: 30% of solar is exported
                    export_revenue = solar_monthly * 0.3 * export_rate
                    net_cost = import_cost - export_revenue

                    months_short = monthly_df.index.strftime('%b')
                    x = np.arange(len(months_short))
                    width = 0.35

                    ax8.bar(x - width/2, import_cost, width, label='Import Cost',
                           color=grid_color, alpha=0.8)
                    ax8.bar(x + width/2, -export_revenue, width, label='Export Revenue',
                           color=solar_color, alpha=0.8)
                    ax8.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
                    ax8.set_xlabel('Month', fontsize=11)
                    ax8.set_ylabel('Cost ($)', fontsize=11)
                    ax8.set_title('Estimated Monthly Costs', fontsize=12, fontweight='bold')
                    ax8.set_xticks(x)
                    ax8.set_xticklabels(months_short, rotation=45)
                    ax8.legend()
                    ax8.grid(True, alpha=0.3)

        # 9. Solar Efficiency by Month
        ax9 = fig.add_subplot(gs[3, 0])
        if not monthly_df.empty and 'Solar_delta' in monthly_df.columns:
            solar_monthly = monthly_df['Solar_delta'].abs()
            months_short = monthly_df.index.strftime('%b')

            # Calculate average daily production for each month
            days_in_month = monthly_df.index.days_in_month
            daily_avg = solar_monthly / days_in_month

            ax9.bar(range(len(daily_avg)), daily_avg, color=solar_color, alpha=0.8)
            ax9.set_xlabel('Month', fontsize=11)
            ax9.set_ylabel('Avg Daily Solar (kWh)', fontsize=11)
            ax9.set_title('Average Daily Solar by Month', fontsize=12, fontweight='bold')
            ax9.set_xticks(range(len(months_short)))
            ax9.set_xticklabels(months_short, rotation=45)
            ax9.grid(True, alpha=0.3)

        # 10. Peak Demand Analysis
        ax10 = fig.add_subplot(gs[3, 1])
        if not daily_df.empty and 'Grid_delta' in daily_df.columns:
            # Group by month and find peak days
            daily_df['month'] = daily_df.index.to_period('M')
            monthly_peaks = daily_df.groupby('month')['Grid_delta'].max().abs()

            if len(monthly_peaks) > 0:
                months_str = [str(m) for m in monthly_peaks.index]
                ax10.bar(range(len(monthly_peaks)), monthly_peaks.values,
                        color=grid_color, alpha=0.8)
                ax10.set_xlabel('Month', fontsize=11)
                ax10.set_ylabel('Peak Daily Demand (kWh)', fontsize=11)
                ax10.set_title('Monthly Peak Demand Days', fontsize=12, fontweight='bold')
                ax10.set_xticks(range(len(months_str)))
                ax10.set_xticklabels(months_str, rotation=45)
                ax10.grid(True, alpha=0.3)

        # 11. Solar vs Grid Correlation
        ax11 = fig.add_subplot(gs[3, 2])
        if not daily_df.empty:
            if 'Grid_delta' in daily_df.columns and 'Solar_delta' in daily_df.columns:
                grid_daily = daily_df['Grid_delta'].abs()
                solar_daily = daily_df['Solar_delta'].abs()

                # Remove outliers for better visualization
                grid_clean = grid_daily[grid_daily < grid_daily.quantile(0.95)]
                solar_clean = solar_daily[solar_daily < solar_daily.quantile(0.95)]

                # Create scatter plot
                ax11.scatter(solar_clean, grid_clean, alpha=0.5, s=20, color='purple')

                # Add trend line
                z = np.polyfit(solar_clean.fillna(0), grid_clean.fillna(0), 1)
                p = np.poly1d(z)
                x_trend = np.linspace(0, solar_clean.max(), 100)
                ax11.plot(x_trend, p(x_trend), "r--", alpha=0.8, linewidth=2)

                ax11.set_xlabel('Solar Production (kWh/day)', fontsize=11)
                ax11.set_ylabel('Grid Import (kWh/day)', fontsize=11)
                ax11.set_title('Solar vs Grid Correlation', fontsize=12, fontweight='bold')
                ax11.grid(True, alpha=0.3)

        # 12. Summary Statistics
        ax12 = fig.add_subplot(gs[3, 3])
        ax12.axis('off')

        summary_text = "SUMMARY STATISTICS\n" + "="*25 + "\n\n"

        if not monthly_df.empty:
            if 'Grid_delta' in monthly_df.columns:
                total_grid = monthly_df['Grid_delta'].abs().sum()
                avg_grid = monthly_df['Grid_delta'].abs().mean()
                summary_text += f"Grid Consumption:\n"
                summary_text += f"  Total: {total_grid:,.0f} kWh\n"
                summary_text += f"  Monthly Avg: {avg_grid:,.0f} kWh\n\n"

            if 'Solar_delta' in monthly_df.columns:
                total_solar = monthly_df['Solar_delta'].abs().sum()
                avg_solar = monthly_df['Solar_delta'].abs().mean()
                summary_text += f"Solar Production:\n"
                summary_text += f"  Total: {total_solar:,.0f} kWh\n"
                summary_text += f"  Monthly Avg: {avg_solar:,.0f} kWh\n\n"

            # Financial summary
            if 'Grid_delta' in monthly_df.columns:
                annual_cost = total_grid * 0.15
                if 'Solar_delta' in monthly_df.columns:
                    solar_savings = total_solar * 0.10  # Estimated savings
                    summary_text += f"Financial (Est.):\n"
                    summary_text += f"  Grid Cost: ${annual_cost:,.0f}\n"
                    summary_text += f"  Solar Savings: ${solar_savings:,.0f}\n"
                    summary_text += f"  Net Benefit: ${(solar_savings-annual_cost):,.0f}"

        ax12.text(0.05, 0.95, summary_text, transform=ax12.transAxes,
                 fontsize=10, verticalalignment='top', fontfamily='monospace',
                 bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

        # Add main title and adjust layout
        fig.suptitle('eGauge Power Monitor - Comprehensive Analysis Dashboard',
                    fontsize=16, fontweight='bold', y=0.98)

        plt.tight_layout()

        # Save figure
        filename = f'egauge_complete_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
        plt.savefig(filename, dpi=150, bbox_inches='tight')
        print(f"\n✅ Dashboard saved to: {filename}")

        plt.show()

    def print_detailed_statistics(self, monthly_df, daily_df, hourly_df):
        """Print detailed statistics report"""

        print("\n" + "="*70)
        print(" "*20 + "DETAILED STATISTICS")
        print("="*70)

        # Monthly Statistics
        if not monthly_df.empty:
            print("\n📊 MONTHLY STATISTICS (Past 12 Months)")
            print("-"*50)

            if 'Grid_delta' in monthly_df.columns:
                grid_monthly = monthly_df['Grid_delta'].abs()
                print(f"\nGrid Consumption:")
                print(f"  Total:        {grid_monthly.sum():>12,.0f} kWh")
                print(f"  Monthly Avg:  {grid_monthly.mean():>12,.0f} kWh")
                print(f"  Peak Month:   {grid_monthly.max():>12,.0f} kWh")
                print(f"  Lowest Month: {grid_monthly.min():>12,.0f} kWh")

            if 'Solar_delta' in monthly_df.columns:
                solar_monthly = monthly_df['Solar_delta'].abs()
                print(f"\nSolar Production:")
                print(f"  Total:        {solar_monthly.sum():>12,.0f} kWh")
                print(f"  Monthly Avg:  {solar_monthly.mean():>12,.0f} kWh")
                print(f"  Peak Month:   {solar_monthly.max():>12,.0f} kWh")
                print(f"  Lowest Month: {solar_monthly.min():>12,.0f} kWh")

            # Calculate self-consumption
            if 'Grid_delta' in monthly_df.columns and 'Solar_delta' in monthly_df.columns:
                total_consumption = grid_monthly.sum()
                total_solar = solar_monthly.sum()
                solar_offset = (total_solar / (total_consumption + total_solar) * 100)
                print(f"\n⚡ Solar Offset: {solar_offset:.1f}% of total consumption")

        # Daily Statistics
        if not daily_df.empty and len(daily_df) > 30:
            print("\n📅 DAILY STATISTICS (Past Year)")
            print("-"*50)

            if 'Grid_delta' in daily_df.columns:
                grid_daily = daily_df['Grid_delta'].abs()
                print(f"\nDaily Grid Usage:")
                print(f"  Average:      {grid_daily.mean():>12,.1f} kWh/day")
                print(f"  Peak Day:     {grid_daily.max():>12,.1f} kWh")
                print(f"  Minimum Day:  {grid_daily.min():>12,.1f} kWh")
                print(f"  Std Dev:      {grid_daily.std():>12,.1f} kWh")

            if 'Solar_delta' in daily_df.columns:
                solar_daily = daily_df['Solar_delta'].abs()
                print(f"\nDaily Solar Production:")
                print(f"  Average:      {solar_daily.mean():>12,.1f} kWh/day")
                print(f"  Peak Day:     {solar_daily.max():>12,.1f} kWh")
                print(f"  Minimum Day:  {solar_daily.min():>12,.1f} kWh")
                print(f"  Std Dev:      {solar_daily.std():>12,.1f} kWh")

        # Hourly Statistics
        if not hourly_df.empty:
            print("\n⏰ HOURLY PATTERNS (Past Week)")
            print("-"*50)

            hourly_df['hour'] = hourly_df.index.hour

            if 'Grid_delta' in hourly_df.columns:
                hourly_grid = hourly_df.groupby('hour')['Grid_delta'].mean().abs()
                peak_hour = hourly_grid.idxmax()
                low_hour = hourly_grid.idxmin()
                print(f"\nGrid Usage by Hour:")
                print(f"  Peak Hour:    {peak_hour:>2d}:00 ({hourly_grid[peak_hour]:.2f} kW avg)")
                print(f"  Lowest Hour:  {low_hour:>2d}:00 ({hourly_grid[low_hour]:.2f} kW avg)")
                print(f"  Daily Range:  {hourly_grid.max() - hourly_grid.min():.2f} kW")

            if 'Solar_delta' in hourly_df.columns:
                hourly_solar = hourly_df.groupby('hour')['Solar_delta'].mean().abs()
                solar_peak = hourly_solar.idxmax()
                print(f"\nSolar Production by Hour:")
                print(f"  Peak Hour:    {solar_peak:>2d}:00 ({hourly_solar[solar_peak]:.2f} kW avg)")
                print(f"  Production Window: {hourly_solar[hourly_solar > 0.1].index[0]}:00 - {hourly_solar[hourly_solar > 0.1].index[-1]}:00")

        # Financial Analysis
        print("\n💰 FINANCIAL ANALYSIS (Estimated)")
        print("-"*50)

        if not monthly_df.empty and 'Grid_delta' in monthly_df.columns:
            import_rate = 0.15  # $/kWh
            export_rate = 0.08  # $/kWh

            total_grid = monthly_df['Grid_delta'].abs().sum()
            annual_grid_cost = total_grid * import_rate

            print(f"\nEstimated Annual Costs:")
            print(f"  Grid Import (@${import_rate}/kWh):  ${annual_grid_cost:>10,.2f}")

            if 'Solar_delta' in monthly_df.columns:
                total_solar = monthly_df['Solar_delta'].abs().sum()
                solar_value = total_solar * import_rate
                export_revenue = total_solar * 0.3 * export_rate  # Assume 30% exported

                print(f"  Solar Value (@${import_rate}/kWh): ${solar_value:>10,.2f}")
                print(f"  Export Revenue (@${export_rate}/kWh): ${export_revenue:>10,.2f}")
                print(f"  Net Savings:                  ${(solar_value - annual_grid_cost):>10,.2f}")
                print(f"  Monthly Avg Savings:          ${((solar_value - annual_grid_cost)/12):>10,.2f}")

        # Peak demand charges (if applicable)
        if not daily_df.empty and 'Grid_delta' in daily_df.columns:
            peak_demand_charge = 15  # $/kW per month
            monthly_peaks = daily_df.groupby(daily_df.index.to_period('M'))['Grid_delta'].max().abs()
            avg_peak = monthly_peaks.mean()

            print(f"\nPeak Demand Charges:")
            print(f"  Avg Monthly Peak: {avg_peak:.1f} kWh/day")
            print(f"  Est. Demand Charge: ${(avg_peak * peak_demand_charge / 24):.2f}/month")

        print("\n" + "="*70)
        print("Analysis Complete!")
        print("="*70)


def main():
    """Main execution function"""
    # Initialize parser and analyzer
    parser = EGaugeDataParser(EGAUGE_IP)
    analyzer = PowerAnalysisReport(parser)

    # Generate complete analysis
    analyzer.generate_complete_analysis()

    # Print final notes
    print("\n📝 NOTES:")
    print("-"*50)
    print("• No authentication required - eGauge has public access enabled")
    print("• Data includes: Grid import/export, Solar production")
    print("• Time ranges: 12 months monthly, 365 days daily, 1 week hourly")
    print("• Cost estimates based on typical residential rates")
    print("• Adjust rates in script for accurate financial analysis")


if __name__ == "__main__":
    main()