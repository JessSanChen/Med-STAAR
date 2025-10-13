# Med-STAAR: Strategic Telehealth Assignments for Adaptive Rostering

By Felix Chen, Jessica Chen. Grand Prize Winner of Rutgers Health Hack 2025.

<img width="1440" height="775" alt="Screenshot 2025-10-12 at 11 55 39 AM" src="https://github.com/user-attachments/assets/75157f36-0665-4d29-8aef-ce5fdc779e34" />
<img width="1440" height="775" alt="Screenshot 2025-10-12 at 11 56 29 AM" src="https://github.com/user-attachments/assets/533195eb-3ebb-425b-87a0-065c3d8745cc" />
<img width="1440" height="775" alt="Screenshot 2025-10-12 at 11 56 51 AM" src="https://github.com/user-attachments/assets/06d2f766-123a-4ad2-aa73-cc6433adebbb" />
<img width="1440" height="775" alt="Screenshot 2025-10-12 at 11 57 00 AM" src="https://github.com/user-attachments/assets/96c40f75-1854-493c-a9f7-bccec834aa08" />
<img width="1440" height="775" alt="Screenshot 2025-10-12 at 11 57 19 AM" src="https://github.com/user-attachments/assets/53e2e08c-8e6e-4427-9562-bf9bae6842eb" />
<img width="1440" height="775" alt="Screenshot 2025-10-12 at 11 57 36 AM" src="https://github.com/user-attachments/assets/e08cc6bb-9c89-4ef8-9b24-9c856f991c54" />
<img width="1440" height="775" alt="Screenshot 2025-10-12 at 11 57 45 AM" src="https://github.com/user-attachments/assets/f56d73f1-95df-4d9c-9a5d-e6f8b7864b03" />

## Contributions
1. Implement two-shot scheduling algorithm using a Constraint-Bound Scheduling Agent and a Completeness-Bound Fair Optimizing Agent to achieves 91% of contract utilization, with Gini coefficient of 0.126
2. Synthesize data + proof of concept forecasting model (ETF with seasonality)
3. Formulate robust scheduling around spikes in patient demand and absences using a Markov Decision Process (MDP)
4. Evaluate fairness 


## Setup
Note that cloning this repo won't allow it to run, as all data input and output files have been privatized.

#### Backend
Install dependencies:
```
python -m pip install -r requirements.txt
```
On `backend/app.py`, run the Flask API:
```
python app.py
```
#### Frontend

```
npm install
npm run dev
```

## Sevaro Challenge Description: Automated Physician Scheduling Agent

### Scheduling Automation Problem Statement 
Telemedicine is rapidly reshaping healthcare delivery. With physician shortages in critical care specialties, providers are increasingly expected to cover multiple hospitals and facilities remotely. Unlike traditional models, a single provider can serve many sites at once—but this creates a scheduling puzzle: how do we fairly and safely assign providers to cover all facilities, while respecting availability, credentialing, consult volumes, and complex organizational rules? 
Your challenge is to design a scheduling automation system for telemedicine. This solution should use provider data, facility requirements, and business rules to automatically generate optimized, fair schedules that ensure high-quality care for patients and sustainable workloads for providers. 

### Inputs Available to You 
* Provider List: Roster of all providers with their contracted number of shifts. 
* Provider Availability: Availability data for the next several months. 
* Credentialing Data: Which sites each provider is credentialed for. 
* Provider Type: Independent Contractor (IC) or Full-Time (FT). 
* Business Rules: A configurable set of rules that govern scheduling. 
* Expected Volume: Predicted consult volume for each site and shift. 
* Sample Schedules: Example schedules for testing and validation. 

### Business Rules to Incorporate 
* Consecutive Shift Restrictions (P1): Limits on how many days in a row providers can be scheduled for each shift type. 
* Credentialing Compliance (P1): Providers cannot be scheduled at sites where they are not credentialed. 
* Daily Hour Limit (P1): Maximum of 12 hours per provider per day. 
* Night Shift Allocation (P2): At least 25% of contracted night shifts must go to full-time providers. 
* Contract Compliance (P1): Total contracted shifts (including weekend requirements) must be honored. 
* Provider Priority (P2): Full-time providers should get preference over part-time or IC providers. 
* Site Grouping Restrictions: Certain high-volume sites should be covered together by the same provider for efficiency. 
* Site Grouping: Certain sites should be grouped together if they are part of the same hospital group 
* Consult Thresholds: A provider’s total consults per shift must remain within safe limits, based on the number of sites they are covering. 

### What Hackathon Teams Will Need to Build 
* Data Model: Represent providers, sites, credentialing, availability, volumes, and contracts. 
* Scheduling Algorithm: Generate valid schedules across multiple sites per provider while enforcing all business rules. 
* Validation Engine: Verify that schedules respect credentialing, workload thresholds, and contractual rules. 
* Optimization Layer (optional): Enhance fairness, reduce provider burnout, and balance workloads. 
* User Interface (bonus points): Provide schedulers with a way to view, validate, and adjust the generated schedule. 

### Why This Matters 
This is more than just a scheduling problem. It’s a challenge at the heart of the future of telemedicine. As more specialties move online, we must build scalable systems that ensure patients across all sites get timely, high-quality care—while preventing provider burnout. By leveraging automation and AI-driven optimization, your solution can directly help address the physician shortage crisis and redefine how healthcare is delivered in the digital age. 

## Evaluation Criteria 
* Ability to generate valid telemedicine schedules that respect all rules and constraints. 
* Ensures full coverage across facilities based on expected consult volumes. 
* Fair distribution of shifts and consults across providers. 
* Reduction in manual scheduling effort. 
* Bonus: Innovative use of AI/ML for predictive consult volumes or optimization. 
