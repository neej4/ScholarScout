# Four modes

ScholarScout can use the same paper search flow for different jobs. The mode changes what gets produced from the papers.

## Academic

For students and researchers. Output: thesis topics, methodology, key papers, novelty check.

Goals: Thesis, Publication, Grant Proposal

The LLM reads papers and asks: "What research gaps exist? What hasn't been studied yet?"

## Product

For builders and entrepreneurs. Output: product name, MVP features, tech stack, revenue model, competitors.

Goals: Hackathon, Side Project, AI Tool, Industry R&D

The LLM reads papers and asks: "What problem does this paper solve that no existing tool addresses?"

## Develop

For developers with an existing project. Output: features, integrations, optimizations directly applicable to your project.

Goals: Feature, Integration, Optimization, Extension, Pivot

The LLM reads papers and asks: "What technique from this paper can improve the project described in context?"

In Develop mode, your context description is a hard constraint. Every idea must be applicable to your project.

## Review

For literature review work. Output: paper clusters, cluster syntheses, and cross-cutting themes.

Review mode requires context so the synthesis has a clear scope.

## How to choose

- First time exploring? Use **Academic** with goal "Any"
- Have a hackathon coming up? Use **Product** with goal "Hackathon"
- Want to improve your existing app? Use **Develop** with goal "Feature" and describe your project in the context field
- Need a literature overview? Use **Review** and describe what the review should focus on
