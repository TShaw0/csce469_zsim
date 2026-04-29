import os
import pprint
import pandas as pd
import numpy as np

# List of test result file locations
locations = ['CARE', 'LFU', 'LRU', 'Rand', 'SRRIP']

benchmark_list = []

resultsBook = {}

for item in locations:
    # Get list of file names in locations
    directory_list = os.listdir(item)
    # For each file in location
    benchmark_dict = {}
    print(f"{item}:")
    for test in directory_list:
        # Append names to a list
        print(f"    {test}")
        if test not in benchmark_list:
            benchmark_list.append(test)
        
        path = item + "/" + test +  "/zsim.out"
        test_dict = {}
        # check zsim.out files
        with open(path, 'r') as file:
            coreSkip = False
            read_state = 0 # traverse - 0 | read core - 1 | read chache - 2 (tack a .5 for stat collection) 
            current_dict = ""
            current_sub_dict = ""
            for line in file:
                line = line.strip() 

                if read_state == 1:
                    if "# Core stats" in line:
                        name = line.split(" ")
                        name = name[0][:-1]
                        current_sub_dict = name
                        test_dict[current_dict][current_sub_dict] = {}
                    elif "Cache stats" not in line:
                        data = line.split(" ")
                        test_dict[current_dict][current_sub_dict][data[0][:-1]] = data[1]
                    else:
                        read_state = 2
                elif "# Core stats" in line:
                    read_state = 1
                    name = line.split(" ")
                    name = name[0][:-1]
                    current_dict = name
                    test_dict[current_dict] = {}
                
                if read_state == 2:
                    if "# Cache stats" and "l3" in line:
                        name = line.split(" ")
                        name = name[0][:-1]
                        current_dict = name
                        test_dict[current_dict] = {}
                        read_state = 2.5
                elif read_state == 2.5:
                    if "# Cache stats" and "l3" in line:
                        name = line.split(" ")
                        name = name[0][:-1]
                        current_sub_dict = name
                        test_dict[current_dict][current_sub_dict] = {}
                    elif "Memory controller stats" not in line:
                        data = line.split(" ")
                        test_dict[current_dict][current_sub_dict][data[0][:-1]] = data[1]
                    else:
                        read_state = 0
                elif "# Cache stats" in line: 
                    if "l3" in line:
                        read_state = 2
                    else: 
                        read_state = 0 

                if "Memory Controller stats" in line:
                    read_state = 0 
        benchmark_dict[test] = test_dict
    resultsBook[item] = benchmark_dict


#pprint.pprint(resultsBook["SRRIP"])
#print(resultsBook['SRRIP'].keys())
#print(resultsBook['SRRIP']['canneal_8c_simlarge'].keys())


def find_it(book, path):
    if isinstance(book, dict):
        chapter_keys = book.keys()
        for item in chapter_keys:
            find_it(book[item], path + " -> " + item)
    else:
        print(path)



# Calculations

# Create pandas dataframe
replacementPolicies = resultsBook.keys()
book_frame = pd.DataFrame(resultsBook)
cycleCount = pd.DataFrame()
ipc = pd.DataFrame()
totalMisses = pd.DataFrame()
mkp1 = pd.DataFrame()

cycleCount['benchmark'] = np.nan
cycleCount['policy'] = np.nan
cycleCount['cycle count'] = np.nan

ipc['benchmark'] = np.nan
ipc['policy'] = np.nan
ipc['ipc'] = np.nan

totalMisses['benchmark'] = np.nan
totalMisses['policy'] = np.nan
totalMisses['total misses'] = np.nan

mkp1['benchmark'] = np.nan
mkp1['policy'] = np.nan
mkp1['mkp1'] = np.nan




for policy in replacementPolicies:
    print(f"{policy}:")
    for benchmark in benchmark_list:
        results = book_frame[policy][benchmark]
        print(f"    {benchmark}")
        if "nan" not in str(results):
            cpu_results = results['westmere'].keys()
            l3_results = results['l3'].keys()
            cycles = 0
            ccylces = 0
            instrs = 0
            mGETS = 0
            mGETXIM = 0
            mGETXSM = 0
            for item in cpu_results:
                cycles += int(results['westmere'][item]['cycles'])
                ccylces += int(results['westmere'][item]['cCycles'])
                instrs += int(results['westmere'][item]['instrs'])
            
            for item in l3_results:
                mGETS += int(results['l3'][item]['mGETS'])
                mGETXIM += int(results['l3'][item]['mGETXIM'])
                mGETXSM += int(results['l3'][item]['mGETXSM'])
            
            total_cycle = cycles + ccylces
            ipc_calc = instrs/total_cycle
            total_misses = mGETS+mGETXIM+mGETXSM
            mkp1_calc = (total_misses/instrs)*1000
            cycleCount.loc[len(cycleCount)] = {"benchmark":benchmark, "cycle count":total_cycle, "policy":policy}
            ipc.loc[len(ipc)] = {"benchmark":benchmark, "ipc":ipc_calc, "policy":policy}
            totalMisses.loc[len(ipc)] = {"benchmark":benchmark, "total misses":total_misses, "policy":policy}
            mkp1.loc[len(ipc)] = {"benchmark":benchmark, "mkp1":mkp1_calc, "policy":policy}

cycleCount = cycleCount.pivot(index='benchmark', columns="policy", values='cycle count')
print(cycleCount)
ipc = ipc.pivot(index='benchmark', columns="policy", values='ipc')
print(ipc)
totalMisses = totalMisses.pivot(index='benchmark', columns="policy", values='total misses')
print(totalMisses)
mkp1 = mkp1.pivot(index='benchmark', columns="policy", values='mkp1')
print(mkp1)

cycleCount.to_csv('cyclecount.csv')
ipc.to_csv('ipc.csv')
totalMisses.to_csv('totalmisses.csv')
mkp1.to_csv('mkp1.csv')