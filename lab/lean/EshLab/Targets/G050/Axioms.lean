/-
EshLab.Targets.G050.Axioms -- prints the axioms of every headline G050 theorem into the build
log (`lake build` output).  Kernel-only results must show exactly
[propext, Classical.choice, Quot.sound]; the LRAT/native results additionally show
Lean.ofReduceBool and Lean.trustCompiler.
-/
import EshLab.Targets.G050.Upper
import EshLab.Targets.G050.UpperLRAT

open EshLab.G050

-- kernel-checked (`decide +kernel`)
#print axioms schur_one
#print axioms schur_two
#print axioms schur_three
#print axioms vdw_two_three
#print axioms schur4_lower
#print axioms vdw3_3_lower
#print axioms vdw2_4_lower
-- LRAT certificate + `native_decide`
#print axioms ViaLRAT.schur2_upper
#print axioms ViaLRAT.schur3_upper
#print axioms ViaLRAT.vdw2_3_upper
#print axioms ViaLRAT.vdw_two_four
#print axioms ViaLRAT.vdw_three_three
