# AMD AI Readiness Assessment — Test Cases

## notes from arryan: for explanation

## What Each Form Question Means (Plain English)

### Step 1: Let's Get Started
- **First Name / Last Name / Work Email** — Self-explanatory. The email is key because the backend uses the domain to look up company data.

### Step 2: About Your Company
- **Company Name** — Who do you work for?
- **Company Size** — How big is the company?
  - **Small Business** = 1-200 people
  - **Mid-Market** = 201-1,000 people
  - **Enterprise** = 1,000+ people
- **Industry** — What sector is the company in? (12 options)

### Step 3: What's Your Role?
Pick the closest match to your job title. It controls the language used in the output (technical vs business framing).

| Option | Label | Covers |
|--------|-------|--------|
| Tech Executive | CTO, CIO, CISO | C-level technical leaders |
| Business Executive | CEO, CFO, COO | C-level business leaders |
| Tech Leadership | VP Eng, VP IT | Senior technical leadership |
| Business Leadership | VP Ops, VP Finance | Senior business leadership |
| Tech Manager | Eng, IT, or Data Mgr | Mid-level technical managers |
| Engineer | Sr Engineer, SysAdmin | Individual contributors |
| Business Ops | Ops, Finance, Procurement | Business operations roles |
| Other | Another role entirely | Anything else |

### Step 4: Your Situation

**"What does your stack look like?" = How modern is your IT infrastructure?**

| You Pick | What It Means | AMD Calls It |
|----------|---------------|--------------|
| Keeping the lights on | Running old on-premise servers, legacy systems, not much cloud | **Observer** |
| In the middle of a shift | Migrating to cloud, mix of old and new | **Challenger** |
| Built for what's next | Fully cloud-native, containers, GPU clusters, ready for AI | **Leader** |

**"Where do you need the biggest improvement?" = What's your #1 business goal right now?**

| You Pick | What It Means |
|----------|---------------|
| Reduce infrastructure overhead | Save money on IT spending |
| Eliminate bottlenecks | Make workloads and delivery faster |
| Build the compute layer for AI | Get infrastructure ready for AI/ML workloads |

**"What's blocking your engineering org?" = What's your biggest obstacle?**

| You Pick | What It Means |
|----------|---------------|
| Legacy systems | Old tech slowing you down |
| Integration friction | Hard to connect your tools and platforms together |
| Resource constraints | Not enough budget, people, or compute |
| Skills gap | Team needs training in cloud or AI |
| Data governance | Compliance, security, or data quality issues |

---

## Test Cases

### 1. Pfizer — Healthcare / Large Enterprise / Technical

| Field | Input |
|-------|-------|
| First Name | Lidia |
| Last Name | Fonseca |
| Email | lidia.fonseca@pfizer.com |
| Company | Pfizer |
| Size | Enterprise |
| Industry | Healthcare |
| Role | Tech Executive (CTO, CIO, CISO) |
| Stack | In the middle of a shift |
| Priority | Eliminate bottlenecks |
| Challenge | Integration friction |

---

### 2. Veeva Systems — Healthcare / Mid-size / Technical

| Field | Input |
|-------|-------|
| First Name | Mike |
| Last Name | Brady |
| Email | mike.brady@veeva.com |
| Company | Veeva Systems |
| Size | Mid-Market |
| Industry | Healthcare |
| Role | Tech Leadership (VP Eng, VP IT) |
| Stack | Built for what's next |
| Priority | Build the compute layer for AI |
| Challenge | Skills gap |

---

### 3. Tempus — Healthcare / Startup / Technical

| Field | Input |
|-------|-------|
| First Name | Sarah |
| Last Name | Chen |
| Email | sarah.chen@tempus.com |
| Company | Tempus |
| Size | Small Business |
| Industry | Healthcare |
| Role | Tech Manager (Eng, IT, or Data Mgr) |
| Stack | Built for what's next |
| Priority | Build the compute layer for AI |
| Challenge | Resource constraints |

---

### 4. JP Morgan Chase — Finance / Large Enterprise / Technical

| Field | Input |
|-------|-------|
| First Name | Pradipto |
| Last Name | Das |
| Email | pradipto.das@jpmchase.com |
| Company | JP Morgan Chase |
| Size | Enterprise |
| Industry | Financial Services |
| Role | Tech Leadership (VP Eng, VP IT) |
| Stack | In the middle of a shift |
| Priority | Eliminate bottlenecks |
| Challenge | Legacy systems |

---

### 5. Affirm — Finance / Mid-Market / Technical

| Field | Input |
|-------|-------|
| First Name | James |
| Last Name | Wang |
| Email | james.wang@affirm.com |
| Company | Affirm |
| Size | Mid-Market |
| Industry | Financial Services |
| Role | Tech Executive (CTO, CIO, CISO) |
| Stack | Built for what's next |
| Priority | Build the compute layer for AI |
| Challenge | Data governance |

---

### 6. Greenlight — Finance / Startup / Business

| Field | Input |
|-------|-------|
| First Name | Rachel |
| Last Name | Morris |
| Email | rachel.morris@greenlight.com |
| Company | Greenlight |
| Size | Small Business |
| Industry | Financial Services |
| Role | Business Ops (Ops, Finance, Procurement) |
| Stack | In the middle of a shift |
| Priority | Reduce infrastructure overhead |
| Challenge | Resource constraints |

---

### 7. Siemens — Manufacturing / Large Enterprise / Technical

| Field | Input |
|-------|-------|
| First Name | Kai |
| Last Name | Toedter |
| Email | kai.toedter@siemens.com |
| Company | Siemens |
| Size | Enterprise |
| Industry | Manufacturing |
| Role | Tech Manager (Eng, IT, or Data Mgr) |
| Stack | Keeping the lights on |
| Priority | Reduce infrastructure overhead |
| Challenge | Legacy systems |

---

### 8. Caterpillar — Manufacturing / Large Enterprise / Business

| Field | Input |
|-------|-------|
| First Name | Mike |
| Last Name | Rogers |
| Email | mike.rogers@caterpillar.com |
| Company | Caterpillar |
| Size | Enterprise |
| Industry | Manufacturing |
| Role | Business Leadership (VP Ops, VP Finance) |
| Stack | Keeping the lights on |
| Priority | Eliminate bottlenecks |
| Challenge | Integration friction |

---

### 9. Protolabs — Manufacturing / Mid-Market / Business

| Field | Input |
|-------|-------|
| First Name | Jen |
| Last Name | Taylor |
| Email | jen.taylor@protolabs.com |
| Company | Protolabs |
| Size | Mid-Market |
| Industry | Manufacturing |
| Role | Business Ops (Ops, Finance, Procurement) |
| Stack | In the middle of a shift |
| Priority | Reduce infrastructure overhead |
| Challenge | Skills gap |

---

### 10. Datadog — Technology / Enterprise / Technical

| Field | Input |
|-------|-------|
| First Name | David |
| Last Name | Mitchell |
| Email | david.mitchell@datadoghq.com |
| Company | Datadog |
| Size | Enterprise |
| Industry | Technology |
| Role | Tech Executive (CTO, CIO, CISO) |
| Stack | Built for what's next |
| Priority | Build the compute layer for AI |
| Challenge | Resource constraints |

---

### 11. Dell — Technology / Large Enterprise / Technical

| Field | Input |
|-------|-------|
| First Name | John |
| Last Name | Roese |
| Email | john.roese@dell.com |
| Company | Dell |
| Size | Enterprise |
| Industry | Technology |
| Role | Tech Executive (CTO, CIO, CISO) |
| Stack | In the middle of a shift |
| Priority | Eliminate bottlenecks |
| Challenge | Legacy systems |

---

### 12. HashiCorp — Technology / Mid-Market / Technical

| Field | Input |
|-------|-------|
| First Name | Alex |
| Last Name | Kumar |
| Email | alex.kumar@hashicorp.com |
| Company | HashiCorp |
| Size | Mid-Market |
| Industry | Technology |
| Role | Engineer (Sr Engineer, SysAdmin) |
| Stack | Built for what's next |
| Priority | Eliminate bottlenecks |
| Challenge | Integration friction |

---

### 13. Empromptu — Technology / Startup / Business

| Field | Input |
|-------|-------|
| First Name | Shane |
| Last Name | Anderson |
| Email | shanea@empromptu.ai |
| Company | Empromptu |
| Size | Small Business |
| Industry | Technology |
| Role | Business Executive (CEO, CFO, COO) |
| Stack | Built for what's next |
| Priority | Build the compute layer for AI |
| Challenge | Resource constraints |

---

### 14. T-Mobile — Telecom / Large Enterprise / Technical

| Field | Input |
|-------|-------|
| First Name | Mark |
| Last Name | Chen |
| Email | mark.chen@t-mobile.com |
| Company | T-Mobile |
| Size | Enterprise |
| Industry | Telecom |
| Role | Tech Leadership (VP Eng, VP IT) |
| Stack | In the middle of a shift |
| Priority | Eliminate bottlenecks |
| Challenge | Legacy systems |

---

### 15. Lumen Technologies — Telecom / Enterprise / Technical

| Field | Input |
|-------|-------|
| First Name | Sandra |
| Last Name | Lopez |
| Email | sandra.lopez@lumen.com |
| Company | Lumen Technologies |
| Size | Enterprise |
| Industry | Telecom |
| Role | Tech Executive (CTO, CIO, CISO) |
| Stack | Keeping the lights on |
| Priority | Reduce infrastructure overhead |
| Challenge | Legacy systems |

---

### 16. Target — Retail / Large Enterprise / Technical

| Field | Input |
|-------|-------|
| First Name | David |
| Last Name | Park |
| Email | david.park@target.com |
| Company | Target |
| Size | Enterprise |
| Industry | Retail |
| Role | Tech Leadership (VP Eng, VP IT) |
| Stack | In the middle of a shift |
| Priority | Build the compute layer for AI |
| Challenge | Data governance |

---

### 17. Chewy — Retail / Mid-Market / Business

| Field | Input |
|-------|-------|
| First Name | Nina |
| Last Name | Shah |
| Email | nina.shah@chewy.com |
| Company | Chewy |
| Size | Mid-Market |
| Industry | Retail |
| Role | Business Ops (Ops, Finance, Procurement) |
| Stack | In the middle of a shift |
| Priority | Reduce infrastructure overhead |
| Challenge | Integration friction |

---

### 18. NextEra Energy — Energy / Large Enterprise / Business

| Field | Input |
|-------|-------|
| First Name | Tom |
| Last Name | Richards |
| Email | tom.richards@nexteraenergy.com |
| Company | NextEra Energy |
| Size | Enterprise |
| Industry | Energy |
| Role | Business Leadership (VP Ops, VP Finance) |
| Stack | Keeping the lights on |
| Priority | Reduce infrastructure overhead |
| Challenge | Legacy systems |

---

### 19. Enphase Energy — Energy / Mid-Market / Technical

| Field | Input |
|-------|-------|
| First Name | Amy |
| Last Name | Foster |
| Email | amy.foster@enphase.com |
| Company | Enphase Energy |
| Size | Mid-Market |
| Industry | Energy |
| Role | Tech Manager (Eng, IT, or Data Mgr) |
| Stack | In the middle of a shift |
| Priority | Eliminate bottlenecks |
| Challenge | Skills gap |

---

### 20. MIT — Education / Enterprise / Technical

| Field | Input |
|-------|-------|
| First Name | Robert |
| Last Name | Williams |
| Email | robert.williams@mit.edu |
| Company | MIT |
| Size | Enterprise |
| Industry | Education |
| Role | Tech Executive (CTO, CIO, CISO) |
| Stack | In the middle of a shift |
| Priority | Build the compute layer for AI |
| Challenge | Resource constraints |

---

### 21. GSA — Government / Large Enterprise / Business

| Field | Input |
|-------|-------|
| First Name | Karen |
| Last Name | Jones |
| Email | karen.jones@gsa.gov |
| Company | General Services Administration |
| Size | Enterprise |
| Industry | Government |
| Role | Business Ops (Ops, Finance, Procurement) |
| Stack | Keeping the lights on |
| Priority | Reduce infrastructure overhead |
| Challenge | Legacy systems |

---

### 22. Spotify — Media / Enterprise / Technical

| Field | Input |
|-------|-------|
| First Name | Chris |
| Last Name | Taylor |
| Email | chris.taylor@spotify.com |
| Company | Spotify |
| Size | Enterprise |
| Industry | Media |
| Role | Tech Leadership (VP Eng, VP IT) |
| Stack | Built for what's next |
| Priority | Eliminate bottlenecks |
| Challenge | Resource constraints |

---

### 23. Progressive — Insurance / Large Enterprise / Business

| Field | Input |
|-------|-------|
| First Name | Laura |
| Last Name | Chen |
| Email | laura.chen@progressive.com |
| Company | Progressive |
| Size | Enterprise |
| Industry | Financial Services |
| Role | Business Executive (CEO, CFO, COO) |
| Stack | In the middle of a shift |
| Priority | Reduce infrastructure overhead |
| Challenge | Data governance |

---

### 24. FedEx — Logistics / Large Enterprise / Technical

| Field | Input |
|-------|-------|
| First Name | Derek |
| Last Name | Patel |
| Email | derek.patel@fedex.com |
| Company | FedEx |
| Size | Enterprise |
| Industry | Other |
| Role | Tech Leadership (VP Eng, VP IT) |
| Stack | Keeping the lights on |
| Priority | Eliminate bottlenecks |
| Challenge | Legacy systems |

---

### 25. CrowdStrike — Cybersecurity / Enterprise / Technical

| Field | Input |
|-------|-------|
| First Name | Megan |
| Last Name | Wu |
| Email | megan.wu@crowdstrike.com |
| Company | CrowdStrike |
| Size | Enterprise |
| Industry | Technology |
| Role | Tech Executive (CTO, CIO, CISO) |
| Stack | Built for what's next |
| Priority | Build the compute layer for AI |
| Challenge | Skills gap |

---

## Coverage Summary

| Dimension | Values Covered |
|-----------|---------------|
| **Industries** | Healthcare (3), Financial Services (3), Manufacturing (3), Technology (4), Telecom (2), Retail (2), Energy (2), Gov/Education (2), Media (1), Insurance (1), Logistics (1), Cybersecurity (1) |
| **Company Size** | Small Business (3), Mid-Market (6), Enterprise (16) |
| **Roles** | Tech Executive (6), Business Executive (2), Tech Leadership (5), Business Leadership (2), Tech Manager (3), Engineer (1), Business Ops (4), Other (0) |
| **Stack (IT Environment)** | Keeping the lights on (5), In the middle of a shift (11), Built for what's next (9) |
| **Priority** | Reduce infrastructure overhead (7), Eliminate bottlenecks (9), Build the compute layer for AI (7) |
| **Challenge** | Legacy systems (7), Integration friction (4), Resource constraints (5), Skills gap (4), Data governance (3) |

## What to Check in Each Output

1. **Company name** — Should match what you entered, not what the API returned
2. **Case study** — Should match the industry:
   - Healthcare → PQR Healthcare
   - Financial Services → PQR Financial
   - Manufacturing / Retail / Energy → Smurfit Westrock
   - Technology / Telecom → KT Cloud
   - Government / Education / Other → PQR General
3. **Personalized hook** — Should reference real company data, not generic filler
4. **CTA** — Should match the buying stage
5. **Role language** — CFO gets ROI talk, engineer gets architecture talk
6. **Stage label** — Observer / Challenger / Leader should match the stack answer
