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
frequencies = [550, 575, 600]
cool_down_voltage = 1166
cool_down_frequency = 400
cool_down_time = 300  # set x time in seconds
benchmark_time = 9000  # set x time in seconds
sample_interval = 150  # set x time in seconds
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

# Add a global flag to track whether the system has already been reset
system_reset_done = False

def handle_sigint(signum, frame):
    global system_reset_done
    if not system_reset_done:
        print(RED + "Benchmarking interrupted by user." + RESET)
        if results:
            reset_to_best_setting()
            save_results()
            print(GREEN + "Bitaxe reset to best or default settings and results saved." + RESET)
        else:
            print(YELLOW + "No valid benchmarking results found. Applying predefined default settings." + RESET)
            set_system_settings(default_voltage, default_frequency)
            restart_system()
        system_reset_done = True
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
    power_consumptions = []
    total_samples = benchmark_time // sample_interval
    
    for sample in range(total_samples):
        info = get_system_info()
        if info is None:
            print(YELLOW + "Skipping this iteration due to failure in fetching system info." + RESET)
            return None, None
        
        temp = info.get("temp")
        if temp is None:
            print(YELLOW + "Temperature data not available." + RESET)
            return None, None, None
        
        if temp >= max_temp:
            print(RED + f"Temperature exceeded {max_temp}°C! Stopping current benchmark." + RESET)
            return None, None, None
        
        hash_rate = info.get("hashRate")
        power_consumption = info.get("power")
        
        if hash_rate is None or power_consumption is None:
            print(YELLOW + "Hashrate or Watts data not available." + RESET)
            return None, None, None
        
        hash_rates.append(hash_rate)
        temperatures.append(temp)
        power_consumptions.append(power_consumption)
        
        # Calculate percentage progress
        percentage_progress = ((sample + 1) / total_samples) * 100
        print(YELLOW + f"Sample {sample + 1}/{total_samples} ({percentage_progress:.2f}% complete) "
                       f"for Core Voltage: {core_voltage}mV, Frequency: {frequency}MHz: "
                       f"Hashrate = {hash_rate} GH/s, Temperature = {temp}°C" + RESET)
        
        time.sleep(sample_interval)
    
    if hash_rates and temperatures and power_consumptions:
        average_hashrate = sum(hash_rates) / len(hash_rates)
        average_temperature = sum(temperatures) / len(temperatures)
        average_power = sum(power_consumptions) / len(power_consumptions)
        efficiency_jth = average_power / (average_hashrate / 1_000) # Convert Gh/s to TH/s
        
        print(GREEN + f"Average Hashrate for Core Voltage: {core_voltage}mV, Frequency: {frequency}MHz = {average_hashrate} GH/s" + RESET)
        print(GREEN + f"Average Temperature for Core Voltage: {core_voltage}mV, Frequency: {frequency}MHz = {average_temperature}°C" + RESET)
        print(GREEN + f"Efficiency: {efficiency_jth:.2f} J/TH" + RESET)
        
        return average_hashrate, average_temperature, efficiency_jth
    else:
        print(YELLOW + "No Hashrate or Temperature or Watts data collected." + RESET)
        return None, None, None

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
            avg_hashrate, avg_temp, efficiency_jth = benchmark_iteration(voltage, freq)
            if avg_hashrate is not None and avg_temp is not None and efficiency_jth is not None:
                results.append({
                    "coreVoltage": voltage,
                    "frequency": freq,
                    "averageHashRate": avg_hashrate,
                    "averageTemperature": avg_temp,
                    "efficiencyJTH": efficiency_jth
                })
            else:
                cool_down()
            save_results()
except Exception as e:
    print(RED + f"An unexpected error occurred: {e}" + RESET)
    if results:
        reset_to_best_setting()
        save_results()
    else:
        print(YELLOW + "No valid benchmarking results found. Applying predefined default settings." + RESET)
        set_system_settings(default_voltage, default_frequency)
        restart_system()
finally:
    if not system_reset_done:
        if results:
            reset_to_best_setting()
            save_results()
            print(GREEN + "Bitaxe reset to best or default settings and results saved." + RESET)
        else:
            print(YELLOW + "No valid benchmarking results found. Applying predefined default settings." + RESET)
            set_system_settings(default_voltage, default_frequency)
            restart_system()

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
            print(GREEN + f"  Efficiency: {result['efficiencyJTH']:.2f} J/TH" + RESET)
    else:
        print(RED + "No valid results were found during benchmarking." + RESET)
