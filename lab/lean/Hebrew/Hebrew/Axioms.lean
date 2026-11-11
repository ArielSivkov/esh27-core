import Hebrew.Theorems
import Hebrew.DR

/-! Axiom report for the main theorems (printed into the `lake build` log).
Expected: `[propext, Classical.choice, Quot.sound]` at most — no `sorryAx`, no
`Lean.ofReduceBool` (we use no `native_decide`). -/

#print axioms Hebrew.lo_adu
#print axioms Hebrew.rh_weekday
#print axioms Hebrew.yearLength_legal
#print axioms Hebrew.yearLength_mem
#print axioms Hebrew.rambam_8_10
#print axioms Hebrew.keviyah_mem_keviyot14
#print axioms Hebrew.keviyot14_occur
#print axioms Hebrew.exactly_14_keviyot
#print axioms Hebrew.keviyah_period
#print axioms Hebrew.greatPeriod_minimal
#print axioms Hebrew.rambam_eq_dr'
