Skills-Gap Intelligence Agent
MSc Computer Science & AI — Muni University
The Skills-Gap Intelligence Agent is a 10-week capstone project that investigates skills mismatches in Uganda's labour market using artificial intelligence, natural language processing and publicly available labour-market and education data.
The project is motivated by Uganda's Fourth National Development Plan (NDPIV), FY2025/26–2029/30, which identifies human-resource and skills challenges and sets national targets including increasing the Science and Technology-to-humanities graduate ratio from 2:5 to 3:5 and reducing unemployment from 11.9% to 8.1%.
NDPIV also calls for the establishment of a functional Labour Market Information System and a National Central Admission System linked to critical skill needs.
Project Objective
The objective is to develop a working prototype that compares
Labour-market demand → Job postings and required skills 
Against
Education/skills supply → Published graduate and enrolment statistics
and produces an explainable picture of potential skills gaps.
Core Components
1.	Data collection and ETL pipeline
2.	Labour-market data storage
3.	Uganda-adapted skills and occupation taxonomy
4.	NLP skill and occupation extraction
5.	Supply-demand gap analysis
6.	NDPIV policy mapping
7.	Policy-facing dashboard/AI interface
8.	Technical and policy evaluation
9.	Ethics and bias assessment
Team
Member	Role
Ayiko Mike - Data & Infrastructure Lead
Aseki Ali	- NLP / ML Lead
Andema Agusto	- Product, Policy & Evaluation Lead

Repository Structure
skills-gap-intelligence/
│
├── README.md
├── data/
│   ├── raw/
│   ├── processed/
│   └── metadata/
│
├── notebooks/
│
├── src/
│   ├── ingestion/
│   ├── preprocessing/
│   ├── taxonomy/
│   ├── nlp/
│   ├── gap_analysis/
│   └── evaluation/
│
├── app/
│
├── models/
│
├── reports/
│
├── docs/
│
├── tests/
│
└── requirements.txt
Ethical Boundaries
The project will:
1.	respect the terms of service of every data source;
2.	avoid prohibited automated collection;
3.	avoid collecting individual job-seeker profiles;
4.	avoid exposing personally identifiable information;
5.	clearly document data limitations;
6.	recognise that online job postings do not represent Uganda's entire labour market;
7.	treat outputs as policy decision support rather than automated decisions.
