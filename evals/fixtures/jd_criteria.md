# Synthetic eval fixture — NOT a real person's criteria.
#
# Held constant so eval runs are reproducible. Two anchors are deliberately
# fictional (Stroom Werkplaats, Kettle Group): no model can have prior knowledge
# of them, so any vibe reasoning about them must come from the `why` field.
# That is the point of case 03.
#
# {{TODAY}} is substituted by run.py so the profile never goes stale and the
# skill never stops to ask an S4 freshness question mid-run.

schema_version: 3
criteria_version: 1
last_updated: {{TODAY}}

history_detail: standard

context:
  role_family: "product management"
  market: "Netherlands, EU-remote"
  languages: ["English", "Dutch"]
  comp_convention: base_plus_var
  fx_rates: {}

profile:
  years_of_experience: 6
  current_title_org: "Product Manager @ Meridiaan Data"
  current_comp:
    amount: 85000
    currency: EUR
    period: year
    basis: total
    notes: "includes 8% holiday allowance"

skills:
  mastered:
    - "SQL"
    - "A/B testing and experiment design"
    - "roadmapping"
    - "stakeholder communication"
  learning:
    - "Kubernetes"
    - "German"
  want_to_learn:
    - "ML fundamentals"

target_roles:
  - id: dev_tools_pm
    name: "Developer tools PM"
    description: "Product manager for tooling used by engineers, close to the technical detail"

hard_gates:
  comp_floor:
    amount: 90000
    currency: EUR
    period: year
    basis: total
  locations: ["Amsterdam", "Utrecht"]
  remote_ok: yes
  intensity_tier: standard
  red_lines:
    - pattern: "individual revenue quota"
      why: "carrying a number changes what the job optimizes for; I want to own a product, not a target"
    - pattern: "on-call rotation"
      why: "health reasons, non-negotiable"

soft_axes:
  target_title_keywords: ["Product Manager", "Senior Product Manager", "Product Lead"]
  target_domains: ["developer tools", "climate tech", "health data"]

  org_traits:
    - trait: "research lab with a shipping product"
      weight: 5
    - trait: "remote-first"
      weight: 4
    - trait: "private-equity owned"
      weight: 1

  vibe_anchors_positive:
    - name: "Basecamp"
      why: "small team, ships deliberately, no growth theater"
    - name: "Stroom Werkplaats"
      why: "a nine-person studio that publishes its reasoning in the open and turns down work that does not fit"

  vibe_anchors_negative:
    - name: "Kettle Group"
      why: "manufactured urgency; metrics used as a loyalty test rather than as information"

axis_weights:
  role_fit: 25
  domain_fit: 20
  org_fit: 15
  vibe_fit: 25
  comp_fit: 15
