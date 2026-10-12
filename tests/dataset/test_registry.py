from speech_delivery.contract.dataset import Category
from speech_delivery.dataset.registry import SOURCES, TEXTS


def test_registry_has_resolved_unique_ids_and_evidence() -> None:
    source_ids = [source.id for source in SOURCES]
    text_ids = [text.id for text in TEXTS]
    assert len(source_ids) == len(set(source_ids))
    assert len(text_ids) == len(set(text_ids))
    assert all(source.rights.evidence_url for source in SOURCES)
    assert all(not source.rights.verified or source.rights.notes for source in SOURCES)
    titles = {source.title for source in SOURCES}
    for text in TEXTS:
        if text.category is not Category.EXTEMPORANEOUS:
            assert text.title in titles
