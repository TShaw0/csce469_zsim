#ifndef RRIP_REPL_H_
#define RRIP_REPL_H_

#include "repl_policies.h"


/* Legacy support.
 * - On each replacement, the controller first calls startReplacement(), indicating the line that will be inserted;
 *   then it calls recordCandidate() for each candidate it finds; finally, it calls getBestCandidate() to get the
 *   line chosen for eviction. When the replacement is done, replaced() is called. The division of getBestCandidate()
 *   and replaced() happens because the former is called in preinsert(), and the latter in postinsert(). Note how the
 *   same restrictions on concurrent insertions extend to this class, i.e. startReplacement()/recordCandidate()/
 *   getBestCandidate() will be atomic, but there may be intervening update() calls between getBestCandidate() and
 *   replaced().
 */
class SRRIPReplPolicy : public LegacyReplPolicy {
private:
    uint32_t* rrpv;
    uint32_t* candArray;

    uint32_t numLines;
    uint32_t numCands;
    uint32_t candIdx;
    uint32_t MAX_RRPV;

public:
    SRRIPReplPolicy(uint32_t _numLines, uint32_t _numCands, uint32_t _maxRPPV)
        : numLines(_numLines), numCands(_numCands), candIdx(0), MAX_RRPV(_maxRPPV)
    {
        rrpv = gm_calloc<uint32_t>(numLines);
        candArray = gm_calloc<uint32_t>(numCands);

        for (uint32_t i = 0; i < numLines; i++) {
            rrpv[i] = MAX_RRPV - 1;
        }
    }

    ~SRRIPReplPolicy() {
        gm_free(rrpv);
        gm_free(candArray);
    }

    void update(uint32_t id, const MemReq* req) {
        rrpv[id] = 0;
    }

    void startReplacement(const MemReq* req) {
        candIdx = 0;
    }

    void recordCandidate(uint32_t id) {
        candArray[candIdx++] = id;
    }

    uint32_t getBestCandidate() {
        while (true) {
            for (uint32_t i = 0; i < candIdx; i++) {
                if (rrpv[candArray[i]] == MAX_RRPV) {
                    return candArray[i];
                }
            }
            for (uint32_t i = 0; i < candIdx; i++) {
                rrpv[candArray[i]]++;
            }
        }
    }

    void replaced(uint32_t id) {
        candIdx = 0;
        rrpv[id] = MAX_RRPV - 1;
    }
};

#endif // RRIP_REPL_H_