# Team 5
### Computer Architecture Simulation Infrastructure for CSCE 469 Computer Architecture

## Project Description

### Project Goals

Our goal with this project is to make an implementation of the CARE cache replacement policy from the paper establishing it by Xiaoyang Lu, Rujia Wang, Xian-He Sun, Et Al. We wanted to make a faithful representation of the policy with multiple tiebreakers depending on the predicted reuse, and the cost of missing due to it not being in the cache. We wanted to compare the performance of this Cache Replacement Policy to Rand (as a baseline because it is like having no replacement policy), LRU (because it is treated as a default policy and it is also locality based), LFU (because it is more advanced and also somewhat default with performance similar to LRU depending on workload), and SRRIP (because it is another locality based policy that is more advanced). CARE is similar to SRRIP, if it also considered the damage of a miss.

### Paper Used

X. Lu, R. Wang and X.-H. Sun, “CARE: A Concurrency-Aware Enhanced Lightweight Cache Management Framework,” 2023 IEEE International Symposium on High-Performance Computer Architecture (HPCA), Montreal, QC, Canada, 2023, pp. 1208–1220, doi: 10.1109/HPCA56546.2023.10071125. https://ieeexplore.ieee.org/document/10071125

## Project Structure

### Files

The project directory has benchmark zip files that are expanded to become the traces of each of the benchmarks we run for this project. It also comes with this readme and the gitignore, the file to setup_environment, the file to parse all the .out files recursively (which is really handy to make your .csv once you get your data), and the zsim_result file containing our data if you want to skip the step of procuring your own data.

### Folders

Once you run the unzip command, all of the benchmark files will be in the "benchmarks" directory. The "tool" directory contains the resuorces to build zsim anytime it is changed. "venv" is your environment put into the directory in order to be able to be used to run testbenches (once you run the venv activate commends). Finally, zsim has all of the files for the simulating tool itself.

#### Within zsim

"build" has all the core zsim files that the average architect will NEVER mess with. "configs" has all of the configuration files. "misc" has all of the files within zsim to make it. "outputs" is the directory created to hold all the output files created by each run. You could also use the .out files in "outputs" to gleam your own data if you think something else that was gathered would be useful. "src" contains the zsim files that architects do change in order to realize their ideas. "tests" seems to have some built in config files for testing. There is also "projectrunscript", which when ran with the correct arguments runs a single testbench with a single cache. In this project specifically, we changed init.cpp, timing_cache.h/.cpp, memory_heirarchy.h/.cpp, and created and edited care_repl.h.

### Heirarchies

zsim/output has the files we changed to make the care implementation, which includes "init.cpp," "care_repl.h," "repl_policies.h," and "timing_cache.h." "rrip_repl.h" was also modified to implement the SRRIP replacement policy. zsim/configs also had to be changed to have copies of the configuration files, but the L3 cache replacement policy implementation was changed to have one for each file. Additionally, the care configs had to have a "timing" element added. 

## How to Simulate in order to Generate our Data

### 1. Clone the directory

Using any git clone method, copy the directory in its entirety to a directory on the machine that you want to run the tests on (most likely a cloud or other computer with a high amount of processing power). For the experiments, we used the Texas A&M Olympus Cloud (ssh NetId@olympus.ece.tamu.edu)

```
git clone https://github.com/CSCE-614-EJKIM-S26/group-5.git
```
or if you have authentication and want to make edits afterward:
```
git clone git@github.com:CSCE-614-EJKIM-S26/group-5.git
```

### 2. Unzip benchmarks files

in root directory

```
$ zip -F benchmarks.zip --out single-benchmark.zip && unzip single-benchmark.zip && mkdir benchmarks/parsec-2.1/inputs/streamcluster
```

### 3. Environemnt setup

#### a. To set up the Python environment for the first time, run the following commands from within the GitHub directory.

```
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install scons
$ source setup_env
```

#### b. If you have ran the venv command in a different directory, you will need to end it before starting it in the GitHub directory.

```
$ rm -rf venv
$ python3 -m venv venv
$ source venv/bin/activate
$ source setup_env
```

#### c. Everytime you want to build or run zsim, you need to setup the environment variables first from within the directory.

```
$ source venv/bin/activate
$ source setup_env
```

### 4. Compile zsim

You need to compile the code each time you make a change.

```
$ cd zsim
$ scons -j4
```

### 5. Run Tests

Run the tests on a bench in a suite with a particular replacement policy

If you are using the Olympus cloud, You will run tests one at a time (in order to not violate lab cloud policies) to collect all the data you need.

Run the tests with each benchmark and replacement policy

```
$ ./projectrunscript <suite (SPEC or PARSEC)> <bench> <repl_pol>
```


All valid options are shown below.

SPEC: ```bzip2, gcc, mcf, hmmer, xalan, sjeng, libquantum, milc, cactusADM, leslie3d, namd, calculix, soplex, lbm```

PARSEC: ```blackscholes, bodytrack, fluidanimate, streamcluster, swaptions, canneal, x264```

repl_policy: ```CARE LRU LFU RandSRRIP ```

### 6. Compile Information

Once you have run tests with all of the benches and replacement policies you want to compare, I have a procedure to automatically combine the information into a file viewable by a spreadsheet program. The file "outfile_parser.py" has already been constructed, and it goes through all the files in a particular directory, and looks at the .log files recursively in that directory in order to determine the runtime data. After that, it stores all the data in a csv. It first sorts it by the replacement policies, then within the replacement policies it sorts them by the benchmark.

In the project main directory
```
$ python3 outfile_parser.py zsim/outputs/project
```

### 7. Chart The Information

Take the .csv file produced in the outfile_parser, and upload it into a spreadsheet program like Excel, Sheets, or Lotus3. You can create whatever type of chart you want, but in order to emulate the charts we made choose a collumn chart. Organize the data with the testbenches in 1 column, and another column for each replacement policy for the measured quantity you are graphing. Set the X-Axis as the test bench collumn, and each of the replacement policy columns as separate series, so they will be plotted alongside eachother for comparison

###### For more information, check `zsim/README.md`
