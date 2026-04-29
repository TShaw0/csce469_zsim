#ifndef CARE_REPL_H_
#define CARE_REPL_H_

#include "repl_policies.h"
#include "timing_cache.h"
#include <algorithm>
//class TimingCache;

#define CARE_RC_MAX  7
#define CARE_PD_MAX  7

// Eviction Priority Value — higher = more evictable
#define CARE_EPV_LOW_REUSE     3  // rc == 0: dead block, evict first
#define CARE_EPV_MOD_LOW_COST  2  // moderate reuse, cheap miss
#define CARE_EPV_MOD_HIGH_COST 1  // moderate reuse, costly miss
#define CARE_EPV_HIGH_REUSE    0  // rc == RC_MAX: hot block, keep last


struct SHTEntry {
    uint32_t rc;  // Re-reference Confidence (0–7)
    uint32_t pd;  // PMC Degree (0–7)
};

class CAREReplPolicy : public LegacyReplPolicy {
  private:
    // Per-line state
    uint32_t* rc; // Re-reference Confidence: a saturating counter that increments on hit, decays on eviction, and is used to predict reuse
    uint32_t* pd; // PMC Degree: an approximation of how costly it would be to re-incur this miss, 
    uint32_t* pmcs; // 3-bit Pure Miss Contribution States
    bool* rBit; // 
    //based on the number of concurrent misses when the line was brought in; used to predict cost
    uint32_t* epv; // Eviction Priority Value: computed from RC and PD to determine eviction order; higher = more evictable
    uint64_t* lineAddr;  // address of the line currently occupying slot id, used to index SHT on eviction
    SHTEntry* sht;
    //TimingCache* timingCache; //used to query active misses for PMC approximation

    // Candidate tracking
    // TEMP NOTE: Reordered variable declaration to make scons happy
    uint32_t* candArray;
    uint32_t  numLines;
    uint32_t  numCands;
    uint32_t  shtEntries; 
    uint32_t  candIdx;

    // DTRM Variables
    uint32_t TMC = 0; // Total Costly Misses
    uint32_t miss_period = 16000; //Number of misses per "period"
    uint32_t current_period = 0;
    uint32_t PMC_high = 350; // Threshold of when a block is considered to be a costly miss
    uint32_t PMC_low = 50; // Threshold of when a block is cosidered a not costly miss
    
    // Incoming request info saved during startReplacement()
    uint64_t incomingAddr;
    uint32_t outstandingMisses;  // rough approximation of N for PMC = 1/N

    uint32_t hashAddr(uint64_t addr) const {
        return (uint32_t)((addr ^ (addr >> 10)) & (shtEntries - 1));
    }

    uint32_t computeEPV(uint32_t rcVal, uint32_t pdVal) const {
        // Low reuse: highest priority for eviction
        if (rcVal == 0)         return CARE_EPV_LOW_REUSE;
        if (rcVal == CARE_RC_MAX) return CARE_EPV_HIGH_REUSE;
        // Moderate reuse: cost determines priority
        return (pdVal == 0) ? CARE_EPV_MOD_LOW_COST : CARE_EPV_MOD_HIGH_COST;
    }

  public:
    CAREReplPolicy(uint32_t _numLines, uint32_t _numCands, uint32_t _shtEntries)
        : numLines(_numLines), numCands(_numCands), shtEntries(_shtEntries), candIdx(0),
          incomingAddr(0), outstandingMisses(0)
    {
        info("[CARE] Care Policy Initialized...");
        rc       = gm_calloc<uint32_t>(numLines);
        pd       = gm_calloc<uint32_t>(numLines);
        epv      = gm_calloc<uint32_t>(numLines);
        lineAddr = gm_calloc<uint64_t>(numLines);
        candArray = gm_calloc<uint32_t>(numCands);
        sht = gm_calloc<SHTEntry>(shtEntries);
        rBit = gm_calloc<bool>(numLines);
        pmcs = gm_calloc<uint32_t>(numLines);
        for (uint32_t i = 0; i < shtEntries; ++i) {
            sht[i].rc = 0;
            sht[i].pd = 0;
        }
        for (uint32_t i = 0; i < numLines; ++i) {
            rc[i]  = 0;
            pd[i]  = 0;
            epv[i] = CARE_EPV_LOW_REUSE;
            pmcs[i] = 0;
            lineAddr[i] = 0;
            rBit[i] = false;
        }
    }

    ~CAREReplPolicy() {
        gm_free(rc);
        gm_free(pd);
        gm_free(epv);
        gm_free(lineAddr);
        gm_free(candArray);
        gm_free(sht);
        gm_free(pmcs);
        gm_free(rBit);
    }

    uint32_t call_hashAddr(uint64_t addr){
        return hashAddr(addr);
    }

    //void setTimingCache(TimingCache* tc) { timingCache = tc; }

    void CareInfoDump(){
        warn("Lines: %d", numLines);
        for(int i = 0; i < numLines; i++){
            if (lineAddr[i] != 0 || lineAddr[i] == 65818){
                info("[CARE] index: %d | Address: %ld", i, lineAddr[i]);
            }
        }
    }

    uint32_t FindID(uint64_t lineAddr_lc){
        uint32_t id = -1;
        for (int i = 0; i < numLines && id == -1; i++){
            if (lineAddr[i] == lineAddr_lc){
                id = i;
            }
        }
        return id;
    }

    void DTRM(double mshrPMC){
        current_period += 1;
        if(mshrPMC >= PMC_high){
            TMC += 1;
        }
        // Update Thresholds
        if (current_period >= miss_period){
            if (((float)TMC/(float)current_period) > 0.05){ // Check if TMC is more than 5% of total misses
                PMC_high += 70;
                PMC_low += 10;
            }
            else if (((float)TMC/(float)current_period) < 0.005){ // Check if TMC is less than 0.5% of total misses
                if (!(PMC_low <= 10)){
                    PMC_high -= 70;
                    PMC_low -= 10;
                }
            }
            current_period = 0;
            TMC = 0;
        }
    }

    // Called on cache hit — promote the line
    void update(uint32_t id, const MemReq* req) {
        if (rBit[id] == false){
            rBit[id] = true;
            if (rc[id] < CARE_RC_MAX) ++rc[id];

            // Feed hit back into SHT
            uint32_t idx = hashAddr(lineAddr[id]);
            if (sht[idx].rc < CARE_RC_MAX) ++sht[idx].rc;

            epv[id] = computeEPV(rc[id], pd[id]);
        }
    }

    void quantizePMC(uint64_t singleLineAddr, double mshrPMC, uint32_t id){
        if (id < numLines){
            // Quantize PMC to PMCS
            if (mshrPMC < PMC_low){
                pmcs[id] = 0;
            }
            else if (mshrPMC > PMC_high){
                pmcs[id] = 3;
            }
            else{
                pmcs[id] = 1;
            }
        }
        else{
            warn("[CARE] quantizePMC: Line Addr out of Bounds!!");
        }

    }

    // Called on Miss Write Back
    void shtPMCUpdate(uint64_t singleLineAddr, double mshrPMC, uint32_t id){
        if (id < numLines){
            uint32_t idx = hashAddr(singleLineAddr);
            if (pmcs[id] == 3 && sht[idx].pd < 7){
                sht[idx].pd += 1;
            }
            else if (pmcs[id] == 0 && sht[idx].pd > 0){
                sht[idx].pd -= 1;
            }
        }
        else{
            warn("[CARE] shtPMCUpdate: Line Addr out of Bounds!!");
        }
    }

    // Called at the start of a replacement — save the incoming address
    void startReplacement(const MemReq* req) {
        candIdx = 0;
        incomingAddr = req->lineAddr;
        //outstandingMisses = timingCache ? timingCache->getActiveMisses() + 1 : 1;
    }

    void recordCandidate(uint32_t id) {
        candArray[candIdx++] = id;
    }

    // Pick the most evictable candidate
    uint32_t getBestCandidate() {
        uint32_t best = candArray[0];
        for (uint32_t i = 1; i < candIdx; ++i) {
            uint32_t cand = candArray[i];
            if (epv[cand] > epv[best]) {
                best = cand;
            } else if (epv[cand] == epv[best]) {
                // Tiebreak 1: lower RC preferred
                if (rc[cand] < rc[best]) {
                    best = cand;
                } else if (rc[cand] == rc[best]) {
                    // Tiebreak 2: direction depends on tier
                    // MOD_HIGH_COST: keep the most costly, evict lowest PD
                    // MOD_LOW_COST:  evict lowest PD (all pd==0 here anyway)
                    // LOW_REUSE:     evict lowest PD (cheapest to re-fetch)
                    if (pd[cand] < pd[best]) {
                        best = cand;
                    }
                }
            }
        }
        return best;
    }

    // Called after eviction of `id`, before the new line is inserted
    void replaced(uint32_t id) {
        //info("[CARE] replace started for id: %d, lineAddr: %ld", id, incomingAddr);
        // Decay SHT RC for the evicted line's address
        // Only decay if this slot held a real line
        if (lineAddr[id] != 0) {
            uint32_t evictIdx = hashAddr(lineAddr[id]);
            if (sht[evictIdx].rc > 0) --sht[evictIdx].rc;
        }

        // Look up SHT for the incoming line
        uint32_t inIdx = hashAddr(incomingAddr);

        // Set RC from SHT prediction
        rc[id] = sht[inIdx].rc;
        

        // Blend pd into SHT PD with saturating update
        if (pd[id] > sht[inIdx].pd && sht[inIdx].pd < CARE_PD_MAX) {
            ++sht[inIdx].pd;
        } else if (pd[id] < sht[inIdx].pd && sht[inIdx].pd > 0) {
            --sht[inIdx].pd;
        }
        pd[id] = sht[inIdx].pd;

        // Record the new line's address so we can look it up on future eviction/hit
        lineAddr[id] = incomingAddr;
        

        epv[id] = computeEPV(rc[id], pd[id]);

        // Reset for next replacement
        candIdx = 0;
        rBit[id] = false;
        pmcs[id] = 0;
        // I'm not sure if I need to reset everything here???
    }
};

#endif  // CARE_REPL_H_