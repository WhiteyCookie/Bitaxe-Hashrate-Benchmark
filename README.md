Bitaxe Benchmarking Script


This repository contains a Python script designed to benchmark the Hashrate performance of a Bitaxe mining device. Tested on the Bitaxe Supra, should work with Ultra too. Hex not sure do the issue of Power Cycle after each new setting.


The script tests various combinations of core voltages and frequencies to determine the optimal settings for maximum hashrate while maintaining safe operating temperatures.



Features


Dynamic Configuration: Automatically fetches and uses the current default settings of the Bitaxe device.


Temperature Monitoring: Continuously monitors the device temperature during benchmarking to prevent overheating.


Automated Benchmarking: Tests different combinations of core voltage and frequency and records the average hashrate and temperature.


Result Storage: Saves the benchmarking results in a JSON file for future analysis.


Graceful Interruption Handling: Captures interruptions (e.g., Ctrl+C) and resets the device to the best or default settings before exiting.


Cooling Down: Automatically cools down the device between benchmarks if necessary.




Configuration


Before running the script, you can customize the following settings in the script:


    bitaxe_ip: IP address of your Bitaxe device (default: "http://192.168.2.117").


    core_voltages: List of core voltages (in mV) to test (default: [1150, 1200, 1250]).


    frequencies: List of frequencies (in MHz) to test (default: [550, 575, 600]).


    cool_down_voltage: Voltage to use during cooldown (default: 1166 mV).


    cool_down_frequency: Frequency to use during cooldown (default: 400 MHz).


    cool_down_time: Duration of cooldown between benchmarks (in seconds, default: 300 seconds).


    benchmark_time: Duration of each benchmark (in seconds, default: 9000 seconds).


    sample_interval: Interval between fetching system data during benchmarking (in seconds, default: 150 seconds).


    max_temp: Maximum allowed temperature before stopping a benchmark (in °C, default: 66°C).


    max_allowed_voltage: Maximum allowed core voltage (in mV, default: 1300 mV). DO ONLY MODIFY IF YOU KNOW WHAT YOU ARE DOING!


    max_allowed_frequency: Maximum allowed frequency (in MHz, default: 600 MHz). DO ONLY MODIFY IF YOU KNOW WHAT YOU ARE DOING!




Usage


To run the script:

    python bitaxe_hashrate_benchmark.py



The script will perform the following actions:


Fetch the default core voltage and frequency from the Bitaxe device.
  
Iterate through the specified voltages and frequencies, applying them to the device and benchmarking their performance.
  
Monitor and record the hashrate and temperature during each benchmark.
  
Save the results to bitaxe_benchmark_results.json.
  
Identify and apply the best performing settings after all benchmarks are completed.

  

Interrupt Handling


If you need to stop the script during benchmarking, simply press Ctrl+C. The script will safely reset the Bitaxe device to the best or default settings and save all results before exiting.
Benchmark Results

After the script finishes, the top 5 performing settings will be displayed in the terminal and saved in the results file.
Example Output:


    Top 5 Performing Settings:

    Rank 1:
    Core Voltage: 1200mV
    Frequency: 590MHz
    Average Hashrate: 555.5 GH/s
    Average Temperature: 60°C
    Efficiency: 23.01 J/TH

    Rank 2:
    Core Voltage: 1250mV
    Frequency: 575MHz
    Average Hashrate: 666.6 GH/s
    Average Temperature: 62°C
    Efficiency: 22.34 J/TH
    ...



Contributions are welcome! Please feel free to submit a pull request or open an issue to suggest improvements.
Acknowledgments


Special thanks to the Bitaxe community and OSMU Discord for their continued support and feedback.
