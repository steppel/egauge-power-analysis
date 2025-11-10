#!/usr/bin/env python3
"""
Quick test script to check eGauge data availability
"""

import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

EGAUGE_IP = "10.10.20.241"

def test_instant_data():
    """Test instant data endpoint"""
    print("Testing instant data endpoint...")
    url = f"http://{EGAUGE_IP}/cgi-bin/egauge?inst"
    response = requests.get(url, timeout=5)

    if response.status_code == 200:
        root = ET.fromstring(response.content)
        print("Current readings:")
        for reg in root.findall('.//r'):
            name = reg.get('n')
            power_element = reg.find('i')
            value_element = reg.find('v')
            if power_element is not None:
                power = float(power_element.text)
                print(f"  {name}: {power:.1f} W ({power/1000:.2f} kW)")
    else:
        print(f"Error: {response.status_code}")

def test_historical_data():
    """Test historical data endpoint"""
    print("\nTesting historical data endpoint...")

    # Try to get last 24 hours of data
    end_time = int(datetime.now().timestamp())
    start_time = int((datetime.now() - timedelta(days=1)).timestamp())

    # Try different URL formats
    urls = [
        f"http://{EGAUGE_IP}/cgi-bin/egauge-show?h&n=24&f={start_time}",
        f"http://{EGAUGE_IP}/cgi-bin/egauge-show?d&n=7",  # Last 7 days
        f"http://{EGAUGE_IP}/cgi-bin/egauge-show?m&n=12",  # Last 12 months
    ]

    for url in urls:
        print(f"\nTrying: {url}")
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print(f"  Success! Response size: {len(response.content)} bytes")
                # Parse first few entries
                root = ET.fromstring(response.content)

                # Check for data format
                if root.find('.//data'):
                    print("  Format: New JSON-like format")
                elif root.find('.//group'):
                    print("  Format: Old XML format")
                    groups = root.findall('.//group')
                    print(f"  Found {len(groups)} data groups")
                elif root.find('.//cname'):
                    print("  Format: Column format")
                    cnames = root.findall('.//cname')
                    print(f"  Columns: {[c.text for c in cnames[:5]]}")
                    rows = root.findall('.//r')
                    print(f"  Data rows: {len(rows)}")
            else:
                print(f"  Error: {response.status_code}")
        except Exception as e:
            print(f"  Exception: {e}")

def test_register_info():
    """Test register information"""
    print("\nTesting register information...")
    url = f"http://{EGAUGE_IP}/cgi-bin/egauge?tot"

    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            print("Total accumulated values:")
            for reg in root.findall('.//r'):
                name = reg.get('n')
                value_element = reg.find('v')
                if value_element is not None:
                    value = float(value_element.text)
                    # Convert from Wh to kWh
                    kwh = value / 1000.0
                    mwh = kwh / 1000.0
                    print(f"  {name}: {kwh:.1f} kWh ({mwh:.2f} MWh)")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print("="*60)
    print("eGAUGE CONNECTION TEST")
    print("="*60)
    print(f"Testing eGauge at {EGAUGE_IP}")
    print(f"Current time: {datetime.now()}")
    print()

    test_instant_data()
    test_register_info()
    test_historical_data()

    print("\n" + "="*60)
    print("TEST COMPLETE")