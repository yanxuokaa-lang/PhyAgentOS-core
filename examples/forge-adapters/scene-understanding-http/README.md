# PAOS HTTP Scene Understanding Adapter

This optional deployment package implements the PAOS
`paos.scene_understanding_inference` factory contract over HTTP/JSON. It has no
model-vendor, simulator, or robot dependency. The service behind the configured
endpoint owns model selection and any vendor-specific request format.

Install the adapter in the deployment environment, create the generic registry,
call `discover()`, and pass the registry plus the `http_json` inference ID and
configuration to the persistent runtime:

```python
registry = SceneUnderstandingInferenceRegistry()
registry.discover()

runtime_providers = {
    "client": client,
    "grasp_provider": grasp_provider,
    "preparation_provider": preparation_provider,
    "capability_provider": capability_provider,
    "resolve_preparation": resolve_preparation,
    "tool_context_provider": tool_context_provider,
}
runtime = build_persistent_runtime(
    **runtime_providers,
    understanding_artifact_resolver=artifact_resolver,
    understanding_inference_registry=registry,
    understanding_inference_id="http_json",
    understanding_inference_configuration={
        "endpoint": "https://inference.example/scene-understanding",
        "timeout_s": 30,
        "token_env": "SCENE_UNDERSTANDING_TOKEN",
    },
)
```

The adapter sends one JSON `POST` containing the PAOS Query fields and
`resolved_artifacts`. Binary artifact `data` is represented as `data_base64`;
`media_type`, artifact references, observation revision, frame, calibration,
and freshness fields are preserved. The server returns a JSON object matching
the existing `scene.understand` result contract. The PAOS endpoint remains the
owner of result and provenance validation.

Configuration keys are `endpoint` (required HTTP(S) URL), `timeout_s` (positive
finite seconds, default 30), `headers` (optional string map), and `token_env`
(optional environment variable read as a Bearer token). Use HTTPS when sending
credentials. Transport, status, and JSON parsing errors propagate to the Query
caller; the adapter does not retry or turn failures into empty results.

No model accuracy, live camera, geometric measurement, grasp, IK, collision, or
motion capability is implied by this transport adapter.
