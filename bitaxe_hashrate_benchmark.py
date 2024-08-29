import requests
import time
import json
import signal
import sys

# ANSI Color Codes
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"

# Configuration
bitaxe_ip = "http://192.168.2.117"
core_voltages = [1150, 1200, 1250]
frequencies = [550, 575, 590]
cool_down_voltage = 1166
cool_down_frequency = 400
cool_down_time = 300  # set x time in seconds
benchmark_time = 9000  # set x time in seconds
fetch_interval = 150  # set x time in seconds
max_temp = 66
max_allowed_voltage = 1300
max_allowed_frequency = 600

# Validate core voltages
if any(voltage > max_allowed_voltage for voltage in core_voltages):
    raise ValueError(RED + f"Error: One or more core voltage values exceed the maximum allowed value of {max_allowed_voltage}mV. Please check the input and try again." + RESET)

# Validate frequency
if any(frequency > max_allowed_frequency for frequency in frequencies):
    raise ValueError(RED + f"Error: One or more frequency values exceed the maximum allowed value of {max_allowed_frequency}Mhz. Please check the input and try again." + RESET)

# Results storage
results = []

# Dynamically determined default settings
default_voltage = None
default_frequency = None

def fetch_default_settings():
    global default_voltage, default_frequency
    try:
        response = requests.get(f"{bitaxe_ip}/api/system/info", timeout=10)
        response.raise_for_status()
        system_info = response.json()
        default_voltage = system_info.get("coreVoltage", 1250)  # Fallback to 1250 if not found
        default_frequency = system_info.get("frequency", 550)  # Fallback to 550 if not found
        print(GREEN + f"Default settings determined:\n"
                      f"  Core Voltage: {default_voltage}mV\n"
                      f"  Frequency: {default_frequency}MHz" + RESET)
    except requests.exceptions.RequestException as e:
        print(RED + f"Error fetching default system settings: {e}. Using fallback defaults." + RESET)
        default_voltage = 1200
        default_frequency = 550

def handle_sigint(signum, frame):
    print(RED + "Benchmarking interrupted by user." + RESET)
    reset_to_best_setting()
    save_results()
    print(GREEN + "Bitaxe reset to best or default settings and results saved." + RESET)
    sys.exit(0)

# Register the signal handler
signal.signal(signal.SIGINT, handle_sigint)

def get_system_info():
    retries = 3
    for attempt in range(retries):
        try:
            response = requests.get(f"{bitaxe_ip}/api/system/info", timeout=10)
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response.json()
        except requests.exceptions.Timeout:
            print(YELLOW + f"Timeout while fetching system info. Attempt {attempt + 1} of {retries}." + RESET)
        except requests.exceptions.ConnectionError:
            print(RED + f"Connection error while fetching system info. Attempt {attempt + 1} of {retries}." + RESET)
        except requests.exceptions.RequestException as e:
            print(RED + f"Error fetching system info: {e}" + RESET)
            break
        time.sleep(5)  # Wait before retrying
    return None

def set_system_settings(core_voltage, frequency):
    settings = {
        "coreVoltage": core_voltage,
        "frequency": frequency
    }
    try:
        response = requests.patch(f"{bitaxe_ip}/api/system", json=settings, timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        print(YELLOW + f"Applying settings: Voltage = {core_voltage}mV, Frequency = {frequency}MHz" + RESET)
        time.sleep(2)
        restart_system()
    except requests.exceptions.RequestException as e:
        print(RED + f"Error setting system settings: {e}" + RESET)

def restart_system():
    try:
        print(YELLOW + "Restarting Bitaxe system to apply new settings..." + RESET)
        response = requests.post(f"{bitaxe_ip}/api/system/restart", timeout=10)
        response.raise_for_status()  # Raise an exception for HTTP errors
        time.sleep(120)  # Allow time for the system to restart
    except requests.exceptions.RequestException as e:
        print(RED + f"Error restarting the system: {e}" + RESET)

def benchmark_iteration(core_voltage, frequency):
    print(GREEN + f"Starting benchmark for Core Voltage: {core_voltage}mV, Frequency: {frequency}MHz" + RESET)
    hash_rates = []
    temperatures = []
    for sample in range(benchmark_time // fetch_interval):
        info = get_system_info()
        if info is None:
            print(YELLOW + "Skipping this iteration due to failure in fetching system info." + RESET)
            return None, None
        temp = info.get("temp")
        if temp is None:
            print(YELLOW + "Temperature data not available." + RESET)
            return None, None
        if temp >= max_temp:
            print(RED + f"Temperature exceeded {max_temp}°C! Stopping current benchmark." + RESET)
            return None, None
        hash_rate = info.get("hashRate")
        if hash_rate is None:
            print(YELLOW + "Hashrate data not available." + RESET)
            return None, None
        hash_rates.append(hash_rate)
        temperatures.append(temp)
        print(YELLOW + f"Sample {sample + 1}: Hashrate = {hash_rate} GH/s, Temperature = {temp}°C" + RESET)
        time.sleep(fetch_interval)
    if hash_rates and temperatures:
        average_hashrate = sum(hash_rates) / len(hash_rates)
        average_temperature = sum(temperatures) / len(temperatures)
        print(GREEN + f"Average Hashrate for Core Voltage: {core_voltage}mV, Frequency: {frequency}MHz = {average_hashrate} GH/s" + RESET)
        print(GREEN + f"Average Temperature for Core Voltage: {core_voltage}mV, Frequency: {frequency}MHz = {average_temperature}°C" + RESET)
        return average_hashrate, average_temperature
    else:
        print(YELLOW + "No hashrate or temperature data collected." + RESET)
        return None, None

def cool_down():
    print(GREEN + f"Cooling down with Core Voltage: {cool_down_voltage}mV, Frequency: {cool_down_frequency}MHz for 5 minutes..." + RESET)
    set_system_settings(cool_down_voltage, cool_down_frequency)
    time.sleep(cool_down_time)
    restart_system()

def save_results():
    try:
        with open("bitaxe_benchmark_results.json", "w") as f:
            json.dump(results, f, indent=4)
        print(GREEN + "Results saved to bitaxe_benchmark_results.json" + RESET)
    except IOError as e:
        print(RED + f"Error saving results to file: {e}" + RESET)

def reset_to_best_setting():
    if not results:
        print(YELLOW + "No valid benchmarking results found. Applying predefined default settings." + RESET)
        set_system_settings(default_voltage, default_frequency)
    else:
        best_result = sorted(results, key=lambda x: x["averageHashRate"], reverse=True)[0]
        best_voltage = best_result["coreVoltage"]
        best_frequency = best_result["frequency"]

        print(GREEN + f"Applying the best settings from benchmarking:\n"
                      f"  Core Voltage: {best_voltage}mV\n"
                      f"  Frequency: {best_frequency}MHz" + RESET)
        set_system_settings(best_voltage, best_frequency)
    
    restart_system()

# Main benchmarking process
try:
    fetch_default_settings()  # Fetch the default settings dynamically at the start
    for voltage in core_voltages:
        for freq in frequencies:
            set_system_settings(voltage, freq)
            avg_hashrate, avg_temp = benchmark_iteration(voltage, freq)
            if avg_hashrate is not None and avg_temp is not None:
                results.append({
                    "coreVoltage": voltage,
                    "frequency": freq,
                    "averageHashRate": avg_hashrate,
                    "averageTemperature": avg_temp
                })
            else:
                cool_down()
            save_results()
except Exception as e:
    print(RED + f"An unexpected error occurred: {e}" + RESET)
    reset_to_best_setting()
    save_results()
finally:
    reset_to_best_setting()
    save_results()

    # Sort results by averageHashRate in descending order and get the top 5
    top_5_results = sorted(results, key=lambda x: x["averageHashRate"], reverse=True)[:5]

    print(GREEN + "Benchmarking completed and Bitaxe reset to best or default settings." + RESET)
    if top_5_results:
        print(GREEN + "\nTop 5 Performing Settings:" + RESET)
        for i, result in enumerate(top_5_results, 1):
            print(GREEN + f"\nRank {i}:" + RESET)
            print(GREEN + f"  Core Voltage: {result['coreVoltage']}mV" + RESET)
            print(GREEN + f"  Frequency: {result['frequency']}MHz" + RESET)
            print(GREEN + f"  Average Hashrate: {result['averageHashRate']} GH/s" + RESET)
            print(GREEN + f"  Average Temperature: {result['averageTemperature']}°C" + RESET)
    else:
        print(RED + "No valid results were found during benchmarking." + RESET)
