# Embodied Knowledge

Use this file for stable, human-authored information about the robot and its environment:

- robot identity and physical limits;
- workspace layout and safety constraints;
- operator conventions;
- facts that are not available from the live Forge Gateway.

Robot execution is available only through the configured Forge Gateway Tool API. Discover live
Tool schemas, bindings, readiness, and frame state with `forge_tool_context`. Never copy live
ToolSpec entries or Gateway endpoints into this file as an execution registry.
