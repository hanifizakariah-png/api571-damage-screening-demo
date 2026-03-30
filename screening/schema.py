EXPECTED_FIELDS = [
    "equipment_tag",
    "unit",
    "service_description",
    "component_type",
    "material",
    "temperature_c",
    "pressure_kpag",
    "phase",
    "water_present",
    "h2s_present",
    "co2_present",
    "chlorides_present",
    "amine_present",
    "caustic_present",
    "sulfur_present",
    "insulation_present",
    "cyclic_service",
    "pwht_status",
    "notes",
]

FIELD_METADATA = {
    "equipment_tag": {
        "label": "Equipment tag",
        "description": "Unique tag or loop identifier used in the facility.",
        "importance": "critical",
    },
    "unit": {
        "label": "Unit",
        "description": "Plant area, process unit, or system name.",
        "importance": "recommended",
    },
    "service_description": {
        "label": "Service description",
        "description": "Short description of the process service or duty.",
        "importance": "critical",
    },
    "component_type": {
        "label": "Component type",
        "description": "Item geometry such as pipe, elbow, drum, exchanger shell, or valve.",
        "importance": "critical",
    },
    "material": {
        "label": "Material",
        "description": "Primary material of construction used for screening.",
        "importance": "critical",
    },
    "temperature_c": {
        "label": "Temperature (C)",
        "description": "Typical operating temperature in degrees Celsius.",
        "importance": "critical",
    },
    "pressure_kpag": {
        "label": "Pressure (kPag)",
        "description": "Typical operating pressure in kPag.",
        "importance": "recommended",
    },
    "phase": {
        "label": "Phase",
        "description": "Gas, liquid, vapor, or multiphase service.",
        "importance": "critical",
    },
    "water_present": {
        "label": "Water present",
        "description": "Whether free water or aqueous phase is present.",
        "importance": "critical",
    },
    "h2s_present": {
        "label": "H2S present",
        "description": "Whether hydrogen sulfide is present in the service.",
        "importance": "critical",
    },
    "co2_present": {
        "label": "CO2 present",
        "description": "Whether carbon dioxide is present in the service.",
        "importance": "critical",
    },
    "chlorides_present": {
        "label": "Chlorides present",
        "description": "Whether chlorides are present in the process or environment.",
        "importance": "critical",
    },
    "amine_present": {
        "label": "Amine present",
        "description": "Whether amine service is present.",
        "importance": "critical",
    },
    "caustic_present": {
        "label": "Caustic present",
        "description": "Whether caustic is present in the service.",
        "importance": "critical",
    },
    "sulfur_present": {
        "label": "Sulfur present",
        "description": "Whether sulfur-bearing species are present.",
        "importance": "critical",
    },
    "insulation_present": {
        "label": "Insulation present",
        "description": "Whether external insulation is present on the item.",
        "importance": "critical",
    },
    "cyclic_service": {
        "label": "Cyclic service",
        "description": "Whether the service is cyclic, batch, or frequently changing.",
        "importance": "recommended",
    },
    "pwht_status": {
        "label": "PWHT status",
        "description": "Post-weld heat treatment condition if known.",
        "importance": "critical",
    },
    "notes": {
        "label": "Notes",
        "description": "Free text for context such as velocity, solids, or special conditions.",
        "importance": "recommended",
    },
}

CRITICAL_FIELDS = [
    field for field, config in FIELD_METADATA.items() if config["importance"] == "critical"
]

RECOMMENDED_FIELDS = [
    field for field, config in FIELD_METADATA.items() if config["importance"] == "recommended"
]
