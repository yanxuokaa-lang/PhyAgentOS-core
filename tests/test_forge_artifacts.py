import pytest

from PhyAgentOS.forge.artifacts import LocalFilesystemArtifactResolver


def test_local_artifact_resolver_reads_payload_and_media_type(tmp_path):
    root = tmp_path / "store"
    artifact = root / "rgb" / "capture.png"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"png-payload")
    resolver = LocalFilesystemArtifactResolver({"camera-store": root})

    resolved = resolver.resolve("artifact://camera-store/rgb/capture.png")

    assert resolved is not None
    assert resolved.data == b"png-payload"
    assert resolved.media_type == "image/png"


def test_local_artifact_resolver_supports_known_non_image_media_types(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    (root / "capture.npy").write_bytes(b"npy-payload")
    (root / "calibration.json").write_bytes(b"{}")
    resolver = LocalFilesystemArtifactResolver({"camera-store": root})

    assert resolver.resolve("artifact://camera-store/capture.npy").media_type == "application/x-npy"
    assert resolver.resolve("artifact://camera-store/calibration.json").media_type == "application/json"


@pytest.mark.parametrize(
    "artifact_ref",
    [
        "https://camera-store/rgb/capture.png",
        "artifact://unknown/rgb/capture.png",
        "artifact://camera-store/../outside.png",
        "artifact://camera-store/%2e%2e/outside.png",
        "artifact://camera-store/rgb%2fcapture.png",
        "artifact://camera-store/rgb/capture.png?download=1",
        "artifact://camera-store:bad/rgb/capture.png",
        "artifact://camera-store/rgb/missing.png",
    ],
)
def test_local_artifact_resolver_rejects_unmapped_or_unsafe_refs(tmp_path, artifact_ref):
    root = tmp_path / "store"
    root.mkdir()
    resolver = LocalFilesystemArtifactResolver({"camera-store": root})

    assert resolver.resolve(artifact_ref) is None


def test_local_artifact_resolver_rejects_symlinks_escaping_root(tmp_path):
    root = tmp_path / "store"
    root.mkdir()
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside")
    (root / "escape.png").symlink_to(outside)
    resolver = LocalFilesystemArtifactResolver({"camera-store": root})

    assert resolver.resolve("artifact://camera-store/escape.png") is None


def test_local_artifact_resolver_requires_existing_roots(tmp_path):
    with pytest.raises(ValueError, match="not a directory"):
        LocalFilesystemArtifactResolver({"camera-store": tmp_path / "missing"})


def test_local_artifact_resolver_requires_authority_roots():
    with pytest.raises(ValueError, match="non-empty authority mapping"):
        LocalFilesystemArtifactResolver({})
