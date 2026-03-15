#ifndef RRIP_REPL_H_
#define RRIP_REPL_H_

#include "repl_policies.h"

// Static RRIP
class SRRIPReplPolicy : public LegacyReplPolicy {
private:
    uint32_t* rrpv;
    uint32_t* candArray;

    uint32_t numLines;
    uint32_t numCands;
    uint32_t candIdx;

    static const uint32_t MAX_RRPV = 3;

public:
    explicit SRRIPReplPolicy(uint32_t _numLines)
        : numLines(_numLines), numCands(_numLines), candIdx(0)
    {
        rrpv = gm_calloc<uint32_t>(numLines);
        candArray = gm_calloc<uint32_t>(numCands);

        for (uint32_t i = 0; i < numLines; i++) {
            rrpv[i] = MAX_RRPV;
        }
    }

    ~SRRIPReplPolicy() {
        gm_free(rrpv);
        gm_free(candArray);
    }

    // On cache hit
    void update(uint32_t id, const MemReq* req) {
        // Predicted to be reused soon
        rrpv[id] = 0;
    }

    void startReplacement(const MemReq* req) {
        candIdx = 0;
    }

    // Record replacement candidates
    void recordCandidate(uint32_t id) {
        candArray[candIdx++] = id;
    }

    // Choose victim
    uint32_t getBestCandidate() {
        while (true) {
            for (uint32_t i = 0; i < candIdx; i++) {
                if (rrpv[candArray[i]] == MAX_RRPV) {
                    return candArray[i];
                }
            }

            // Increment RRPVs if no candidate at MAX
            for (uint32_t i = 0; i < candIdx; i++) {
                if (rrpv[candArray[i]] < MAX_RRPV) {
                    rrpv[candArray[i]]++;
                }
            }
        }
    }

    // When a line is replaced
    void replaced(uint32_t id) {
        // Insert with long re-reference prediction
        rrpv[id] = MAX_RRPV - 1;
    }
};
#endif // RRIP_REPL_H_
