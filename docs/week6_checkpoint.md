# Week 6 Checkpoint (team post draft)

1. **Units.** Demand: one de-duplicated vacancy posting for a job in Uganda. Supply: one graduate on a published 2025 graduation list.

2. **Primary gap.** G = 100 × (demand share − supply share) per Week 4 domain, in percentage points. Shares put postings and graduates on one scale; the difference stays defined when a side is zero and sums to zero across categories.

3. **Versions.** Week 3 records v0.1.0 (working split, sha256 2eacce91…, Week 8 held-out excluded), taxonomy v0.1 (provisional), extraction v1.0-gazetteer-spacy, engine w6-gap-0.1.0.

4. **Largest gaps** (denominators: 13 postings, 3,585 graduates). Positive: DOM-10 Transport, logistics and supply chains, +10.2 pp (2 postings, 187 graduates). Negative: DOM-07 Public policy and governance, −16.0 pp. Both are LOW SUPPORT and their 90% bootstrap intervals cross zero.

5. **STEM:humanities.** 0.11:5 on the supply sample (71 STEM, 3,331 humanities, health held out); 0.38:5 if health counts as STEM. NDPIV para 441(iv) (cited as 441(ii) in the brief) sets graduates at 2:5 in FY2022/23 and 3:5 by 2029/30. We label this non-comparable: two management/law-heavy institutions, mostly postgraduate awards.

6. **Surprising result.** Business and administration is about half of both demand and supply, so its gap is small, but its sign flips when the two largest UMI programmes are dropped. That reflects which institutions we sampled, not the market.

7. **Joins.** All records mapped. Uncertain: 5 postings and 10 programmes, chiefly Bachelor of Laws (329 graduates) to DOM-07 because the taxonomy has no legal domain. Week 5 extraction agrees with our rules for 14 of 17 records. Six domains have no evidence on either side, including informal work.

8. **Checks.** Bootstrap intervals plus seven sensitivity scenarios: certain-only mappings, jobs outside Uganda, intermediaries removed, exact counts only, Week 5 mappings first, and largest programmes dropped.

9. **Week 7 must avoid** any national shortage or STEM-ratio claim, and any category result shown without its denominator, interval and support label.

10. **Help needed.** A supervisor ruling on health and law in the STEM:humanities split, and more demand data with posting descriptions before the interface means anything.
