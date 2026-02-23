
def assess_weaning_readiness(fio2_percent, peep, gcs, hemodynamically_stable,
                              no_new_sedation_24h, rr_during_trial=None,
                              spo2_during_trial=None, no_distress=None):
    sat_criteria = {
        "FiO2 <= 50%":             fio2_percent <= 50,
        "PEEP <= 8 cmH2O":         peep <= 8,
        "GCS >= 8":                gcs >= 8,
        "Hemodynamically stable":  hemodynamically_stable,
        "No new sedation in 24h":  no_new_sedation_24h,
    }
    sat_passed  = sum(sat_criteria.values())
    sat_total   = len(sat_criteria)
    sat_ready   = sat_passed == sat_total
    sat_failing = [k for k, v in sat_criteria.items() if not v]

    sbt_criteria = {}
    sbt_failing  = []
    if rr_during_trial   is not None: sbt_criteria["RR < 35 during trial"]           = rr_during_trial < 35
    if spo2_during_trial is not None: sbt_criteria["SpO2 >= 90% during trial"]       = spo2_during_trial >= 90
    if no_distress       is not None: sbt_criteria["No increased work of breathing"]  = no_distress
    if sbt_criteria:
        sbt_ready   = all(sbt_criteria.values())
        sbt_failing = [k for k, v in sbt_criteria.items() if not v]
    else:
        sbt_ready = None

    if not sat_ready:
        status = "NOT READY"
        recommendation = "Patient does NOT meet SAT criteria yet"
        next_step = f"Address failing criteria: {', '.join(sat_failing)}. Reassess in 4-8 hours."
    elif sbt_criteria and not sbt_ready:
        status = "SAT PASSED / SBT FAILED"
        recommendation = "SAT criteria met but SBT criteria not met"
        next_step = f"SBT failing: {', '.join(sbt_failing)}. Rest patient, retry SBT tomorrow."
    elif sat_ready and not sbt_criteria:
        status = "READY FOR SBT TRIAL"
        recommendation = "Patient meets SAT criteria — proceed to SBT"
        next_step = "Start 30-min SBT on pressure support 5-8 cmH2O or T-piece. Monitor RR, SpO2, work of breathing."
    else:
        status = "CONSIDER EXTUBATION"
        recommendation = "Patient meets both SAT and SBT criteria"
        next_step = "Discuss extubation with team. Ensure cuff leak, airway protection, secretions manageable. Keep reintubation equipment at bedside."

    return {
        "weaning_status": status, "recommendation": recommendation, "next_step": next_step,
        "sat_criteria": sat_criteria, "sat_score": f"{sat_passed}/{sat_total}",
        "sbt_criteria": sbt_criteria if sbt_criteria else "Not yet assessed",
        "failing_criteria": sat_failing + sbt_failing,
        "caution": "Screening tool only. Extubation requires full clinical assessment.",
        "safety_note": "[AI Decision Support Only — Clinical judgment required]"
    }
