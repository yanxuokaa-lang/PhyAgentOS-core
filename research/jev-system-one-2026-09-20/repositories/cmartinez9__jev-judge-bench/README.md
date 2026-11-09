# jev-judge-bench

A bench for comparing **binary LLM judges**: the same pass/fail rubrics graded once by
[Jev](https://typesafe.ai/blog/introducing-system-one-models-and-jev) (TypeSafe's System One
model) and once by a frontier model, measured on speed, cost, and agreement with human labels.

Jev's `Noul` primitive answers a yes/no question as a calibrated probability in 70–500ms, which
makes it a binary judge in its own right. The question this bench answers is what you give up
when you swap an expensive frontier judge for it.

Scaffolding in progress.
