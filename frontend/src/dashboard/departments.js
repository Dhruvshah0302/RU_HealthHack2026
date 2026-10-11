/* The teams that receive patient requests.

   Clinical requests all go to the Clinical team (nursing answers first and brings in the
   physician, respiratory therapy, pharmacy or PT/OT as needed). Everything else goes to the
   support team that does that work.

   `codes` lists the codes that mean this team. Tickets carry `team` (app/teams.py); older
   tickets with only `department` still land on the right screen through these aliases.

   Colours identify the team and are far apart on the colour wheel. Red is kept for urgency
   (Emergency, Urgent), so no team uses it. */
export const DEPARTMENTS = [
  {
    key: "clinical", name: "Clinical", group: "clinical", color: "#0F62FE",
    codes: ["nurse", "clinical"],
    covers: "Nursing first; physician, respiratory therapy, pharmacy and PT/OT through nursing",
  },
  {
    key: "unit_clerk", name: "Unit Clerk", group: "support", color: "#4D5B6A",
    codes: ["unit_clerk", "unit_clerk_it"],
    covers: "Desk triage, phone, visitors, Wi-Fi and TV account help",
  },
  {
    key: "environmental_services", name: "Housekeeping", short: "Housekeeping", group: "support", color: "#198038",
    codes: ["environmental_services", "housekeeping_facilities", "housekeeping"],
    covers: "Cleaning, spills, trash, fresh linens",
  },
  {
    key: "food_services", name: "Food & Nutrition", group: "support", color: "#E07B00",
    codes: ["food_services", "dietary"],
    covers: "Meals, snacks, drinks, dietary questions",
  },
  {
    key: "facilities_biomed", name: "Facilities & Biomed", group: "support", color: "#007D79",
    codes: ["facilities_biomed", "facilities"],
    covers: "Room temperature, broken TV or bed, equipment faults",
  },
  {
    key: "patient_advocacy", name: "Patient Advocacy", group: "support", color: "#6929C4",
    codes: ["patient_advocacy"],
    covers: "Complaints, interpreters, patient rights",
  },
  {
    key: "case_management", name: "Case Management", group: "support", color: "#B0389C",
    codes: ["case_management", "social_work"],
    covers: "Insurance, post-discharge care, home equipment, social work",
  },
];

const BY_CODE = Object.fromEntries(DEPARTMENTS.flatMap((d) => d.codes.map((c) => [c, d])));

// Team for a backend department code. A code this screen does not know is never dropped:
// it goes to Clinical, the same safe default the routing uses, marked so staff can see why.
export function teamFor(code) {
  return BY_CODE[code] || { ...DEPARTMENTS[0], unknownCode: code };
}

export const findTeam = (key) => DEPARTMENTS.find((d) => d.key === key);
