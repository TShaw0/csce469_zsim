# Team 5
Computer Architecture Simulation Infrastructure for CSCE 469 Computer Architecture


### 1. Unzip benchmarks files

in root directory

```
$ zip -F benchmarks.zip --out single-benchmark.zip && unzip single-benchmark.zip && mkdir benchmarks/parsec-2.1/inputs/streamcluster
```

### 2. Environemnt setup

#### a. To set up the Python environment for the first time, run the following commands.

```
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install scons
```

#### b. If you have ran the venv command in a different directory, you will need to end it before starting it in this directory

```
$ rm -rf venv
$ python3 -m venv venv
$ source venv/bin/activate
```

#### c. Everytime you want to build or run zsim, you need to setup the environment variables first.

```
$ source venv/bin/activate
$ source setup_env
```

### 3. Compile zsim

You need to compile the code each time you make a change.

```
$ cd zsim
$ scons -j4
$ cd ../
```

### 4. Run Tests

Run the tests on a bench in a suite with a particular replacement policy

You will run tests one at a time (in order to not violate lab cloud policies) to collect all the data you need

Run the tests with each benchmark and replacement policy

```
$ ./hw2rinscript <suite (SPEC or PARSEC)> <bench> <repl_pol>
$ ./projectrunscript <suite (SPEC or PARSEC)> <bench> <repl_pol>
$ ./projectrunscript <suite (SPEC or PARSEC)> <bench> <repl_pol>
```

```

###### For more information, check `zsim/README.md`
