from vericode import differential_analysis, generate_candidates, select_candidate, spec_from_requirement, verify

requirement = "Return the area of a circle for a non-negative radius r."

candidates = generate_candidates(requirement, n=3, func_name="area")
for i, code in enumerate(candidates):
    print(f"--- candidate {i}\n{code}")

analysis = differential_analysis(candidates, "area", arity=1)
chosen = select_candidate(analysis)
print("clusters:", chosen["clusters"], "selected:", chosen["selected"])

spec = spec_from_requirement(requirement, "area", ["r"])
print(spec)

print(verify(chosen["code"], spec))