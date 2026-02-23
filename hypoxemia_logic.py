
ARDSNET_TABLE = {
    30:  (5,  5),  40:  (5,  8),  50:  (8,  10),
    60:  (10, 10), 70:  (10, 14), 80:  (10, 14),
    90:  (14, 16), 100: (18, 24),
}

def get_ardsnet_peep(fio2_percent, strategy="low"):
    table_keys = sorted(ARDSNET_TABLE.keys())
    closest = min(table_keys, key=lambda x: abs(x - fio2_percent))
    low_peep, high_peep = ARDSNET_TABLE[closest]
    recommended = low_peep if strategy == "low" else high_peep
    return {"fio2_used": closest, "recommended_peep": recommended,
            "low_peep_option": low_peep, "high_peep_option": high_peep}

def classify_hypoxemia_severity(spo2):
    if spo2 < 85:
        return {"severity": "CRITICAL", "urgency": "EMERGENCY",
                "immediate_action": "🚨 SpO2 below 85% — assess patient PHYSICALLY RIGHT NOW. Check tube, circuit, pulse.",
                "escalate": True}
    elif spo2 < 88:
        return {"severity": "SEVERE", "urgency": "URGENT",
                "immediate_action": "SpO2 under 88% — increase FiO2 immediately and investigate cause.",
                "escalate": False}
    elif spo2 < 92:
        return {"severity": "MODERATE", "urgency": "PROMPT",
                "immediate_action": "SpO2 below target — adjust FiO2 or PEEP and monitor.",
                "escalate": False}
    else:
        return {"severity": "ACCEPTABLE", "urgency": "ROUTINE",
                "immediate_action": "SpO2 within acceptable range. Continue monitoring.",
                "escalate": False}

def calculate_pf_ratio(pao2, fio2_percent):
    if fio2_percent <= 0 or fio2_percent > 100:
        return {"error": "FiO2 must be between 1 and 100"}
    pf_ratio = pao2 / (fio2_percent / 100)
    if pf_ratio > 300:
        category = "No ARDS"
        recs = ["Continue current settings"]
    elif pf_ratio > 200:
        category = "Mild ARDS"
        recs = ["Ensure 6 mL/kg IBW tidal volume", "Optimize PEEP with ARDSnet low-PEEP table"]
    elif pf_ratio > 100:
        category = "Moderate ARDS"
        recs = ["Lung-protective ventilation mandatory", "Consider high-PEEP strategy", "Prone positioning strongly recommended"]
    else:
        category = "Severe ARDS"
        recs = ["🚨 Prone positioning immediately", "High PEEP strategy", "ECMO consultation if P/F < 80", "Escalate to senior intensivist NOW"]
    return {"pf_ratio": round(pf_ratio, 1), "ards_category": category,
            "recommendations": recs, "note": "Berlin Definition 2012"}

def hypoxemia_action_plan(spo2, fio2_percent, current_peep, pao2=None):
    severity_info = classify_hypoxemia_severity(spo2)
    fio2_is_high  = fio2_percent >= 60
    fio2_is_max   = fio2_percent >= 95
    peep_is_high  = current_peep >= 12
    actions = []

    if severity_info["urgency"] == "EMERGENCY":
        actions.append({"priority": 1,
            "action": "🚨 STOP — Physically assess patient IMMEDIATELY",
            "reason": "SpO2 < 85% may indicate tube dislodgement or pneumothorax"})

    if not fio2_is_high:
        new_fio2 = min(fio2_percent + 20, 100)
        actions.append({"priority": 2,
            "action": f"Increase FiO2 from {fio2_percent}% to {new_fio2}%",
            "reason": "Safe headroom below 60% toxicity threshold — fastest fix"})
    elif not fio2_is_max:
        ardsnet = get_ardsnet_peep(fio2_percent, strategy="high")
        if ardsnet["recommended_peep"] > current_peep:
            actions.append({"priority": 2,
                "action": f"Increase PEEP from {current_peep} to {ardsnet['recommended_peep']} cmH2O (ARDSnet high-PEEP)",
                "reason": "FiO2 >= 60% — recruit collapsed lung units via PEEP",
                "caution": "⚠️ Monitor blood pressure after each PEEP increase"})

    if fio2_is_max and peep_is_high:
        actions.append({"priority": 1,
            "action": "Escalate to senior intensivist — consider prone positioning and ECMO",
            "reason": "Patient on maximum support settings"})

    pf_result = None
    if pao2:
        pf_result = calculate_pf_ratio(pao2, fio2_percent)
        actions.append({"priority": 3,
            "action": f"P/F ratio = {pf_result['pf_ratio']} — {pf_result['ards_category']}",
            "reason": "Guides further escalation decisions"})

    actions.append({"priority": 4,
        "action": "Reassess SpO2 and BP 5-10 minutes after each change",
        "reason": "Vent changes need time to show full effect"})

    return {
        "urgency": severity_info["urgency"],
        "severity": severity_info["severity"],
        "immediate_message": severity_info["immediate_action"],
        "action_plan": sorted(actions, key=lambda x: x["priority"]),
        "pf_analysis": pf_result,
        "safety_note": "[AI Decision Support Only — Clinical judgment required]"
    }
