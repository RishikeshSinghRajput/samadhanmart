import { useMemo } from "react";
import { getAllStates, getDistricts } from "india-state-district";

const states = getAllStates().sort((a, b) => a.name.localeCompare(b.name));

export default function LocationFields({
  state,
  district,
  onChange,
  className = "",
  required = true,
}) {
  const stateCode = states.find((entry) => entry.name === state)?.code;
  const districts = useMemo(() => stateCode ? getDistricts(stateCode) : [], [stateCode]);

  return (
    <div className={`location-fields ${className}`}>
      <label className="field">
        State
        <select
          required={required}
          value={state}
          onChange={(event) => onChange({ state: event.target.value, district: "" })}
        >
          <option value="">{required ? "Select state / UT" : "All states"}</option>
          {states.map((entry) => <option key={entry.code} value={entry.name}>{entry.name}</option>)}
        </select>
      </label>
      <label className="field">
        District
        <select
          required={required}
          disabled={!state}
          value={district}
          onChange={(event) => onChange({ state, district: event.target.value })}
        >
          <option value="">{state ? (required ? "Select district" : "All districts") : (required ? "Select a state first" : "All districts")}</option>
          {districts.map((name) => <option key={name} value={name}>{name}</option>)}
        </select>
      </label>
    </div>
  );
}
