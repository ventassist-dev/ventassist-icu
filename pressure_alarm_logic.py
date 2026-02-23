
def classify_pressure_alarm(peak_pressure, plateau_pressure=None, peep=5, tidal_volume_ml=None, ibw_kg=None):
    actions = []
    driving_pressure = None
    dp_status = None

    if peak_pressure < 35:
        return {
            "urgency": "ROUTINE", "peak_pressure": peak_pressure,
            "problem_category": "Normal — no alarm",
            "assessment": "Peak pressure within acceptable range",
            "actions": [{"priority": 1, "action": "Continue monitoring", "reason": "Pressure within safe range"}],
            "driving_pressure": None, "driving_pressure_status": None,
            "tidal_volume_warning": None,
            "safety_note": "[AI Decision Support Only]"
        }

    if plateau_pressure:
        driving_pressure = plateau_pressure - peep
        if driving_pressure >= 18:   dp_status = "DANGEROUS"
        elif driving_pressure >= 15: dp_status = "ELEVATED"
        else:                        dp_status = "ACCEPTABLE"

    if plateau_pressure is None:
        problem_category = "Unknown — plateau pressure needed"
        actions = [
            {"priority": 1, "action": "Perform inspiratory hold to measure plateau pressure",
             "reason": "Distinguishes airway from lung problems"},
            {"priority": 2, "action": "Visually inspect circuit for kinks or disconnection",
             "reason": "Quick check while preparing hold maneuver"}
        ]
    elif plateau_pressure <= 30:
        problem_category = "AIRWAY / CIRCUIT PROBLEM"
        actions = [
            {"priority": 1, "action": "Suction the endotracheal tube",
             "reason": "Secretions are the most common cause"},
            {"priority": 2, "action": "Check for tube biting — insert bite block",
             "reason": "Biting collapses the tube lumen"},
            {"priority": 3, "action": "Inspect circuit for kinks, water, disconnection",
             "reason": f"Peak-to-plateau gradient of {peak_pressure - plateau_pressure} cmH2O suggests resistance"},
            {"priority": 4, "action": "Check ETT position — rule out right mainstem intubation",
             "reason": "Tube migration causes high pressures"}
        ]
    else:
        problem_category = "LUNG / CHEST WALL PROBLEM"
        actions = [
            {"priority": 1, "action": "🚨 Rule out tension pneumothorax IMMEDIATELY",
             "reason": "High Pplat + instability = tension pneumo until proven otherwise"},
            {"priority": 2, "action": "Reduce tidal volume — target driving pressure < 15 cmH2O",
             "reason": f"Plateau {plateau_pressure} cmH2O exceeds limit. DP = {driving_pressure} ({dp_status})"},
            {"priority": 3, "action": "Consider bronchospasm — listen for wheeze, give bronchodilator",
             "reason": "Bronchospasm raises both peak and plateau pressure"},
            {"priority": 4, "action": "Check for auto-PEEP — reduce RR by 2-4 breaths/min",
             "reason": "Air trapping causes breath stacking"},
            {"priority": 5, "action": "Order urgent CXR and ABG",
             "reason": "Identify underlying cause"}
        ]

    vt_warning = None
    if tidal_volume_ml and ibw_kg:
        vt_per_kg = tidal_volume_ml / ibw_kg
        if vt_per_kg > 8:
            vt_warning = f"⚠️ Tidal volume {vt_per_kg:.1f} mL/kg IBW exceeds limit. Reduce to {round(ibw_kg*6)} mL."

    return {
        "urgency": "URGENT" if peak_pressure >= 40 else "PROMPT",
        "peak_pressure": peak_pressure, "plateau_pressure": plateau_pressure,
        "driving_pressure": driving_pressure, "driving_pressure_status": dp_status,
        "problem_category": problem_category,
        "actions": sorted(actions, key=lambda x: x["priority"]),
        "tidal_volume_warning": vt_warning,
        "safety_note": "[AI Decision Support Only — Clinical judgment required]"
    }

def calculate_ideal_body_weight(height_cm, sex):
    height_inches = height_cm / 2.54
    ibw = (50 + 2.3*(height_inches-60)) if sex.lower() in ["male","m"] else (45.5 + 2.3*(height_inches-60))
    ibw = max(ibw, 30)
    return {"ideal_body_weight_kg": round(ibw,1), "safe_tidal_volume_ml": round(ibw*6),
            "max_tidal_volume_ml": round(ibw*8), "note": "Always use IBW not actual weight"}
