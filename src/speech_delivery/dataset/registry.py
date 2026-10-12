"""Frozen, rights-evidenced source and text registry for the dataset build."""

from pathlib import Path

from speech_delivery.contract.dataset import (
    Category,
    License,
    RightsEvidence,
    Sex,
    SourceRecord,
    TextRecord,
)

_ARCHIVE = "https://archive.org"


def _rights(identifier: str, license: License, licenseurl: str) -> RightsEvidence:
    return RightsEvidence(
        license=license,
        evidence_url=licenseurl,
        verified=True,
        notes=(
            f"Verified in this build session from {_ARCHIVE}/metadata/{identifier}: "
            f"metadata licenseurl is {licenseurl!r}."
        ),
    )


_PDM = "http://creativecommons.org/publicdomain/mark/1.0/"
_PD = "http://creativecommons.org/licenses/publicdomain/"

SOURCES: tuple[SourceRecord, ...] = (
    SourceRecord(
        id="new-colossus-alg",
        title="The New Colossus",
        speaker_name="ALG",
        speaker_sex=Sex.UNSPECIFIED,
        page_url=f"{_ARCHIVE}/details/newcolossus_1207_librivox",
        audio_url=f"{_ARCHIVE}/download/newcolossus_1207_librivox/newcolossus_lazarus_alg.mp3",
        excerpt_start=0.0,
        excerpt_end=62.14,
        rights=_rights("newcolossus_1207_librivox", License.PUBLIC_DOMAIN_MARK, _PDM),
    ),
    SourceRecord(
        id="ozymandias-add",
        title="Ozymandias",
        speaker_name="ADD",
        speaker_sex=Sex.UNSPECIFIED,
        page_url=f"{_ARCHIVE}/details/ozymandias_librivox",
        audio_url=f"{_ARCHIVE}/download/ozymandias_librivox/ozymandias_of_egypt_shelley_add.mp3",
        excerpt_start=0.0,
        excerpt_end=88.11,
        rights=_rights("ozymandias_librivox", License.PUBLIC_DOMAIN_MARK, _PD),
    ),
    SourceRecord(
        id="gettysburg-address-amb",
        title="The Gettysburg Address",
        speaker_name="AMB",
        speaker_sex=Sex.UNSPECIFIED,
        page_url=f"{_ARCHIVE}/details/gettysburgaddress_150anniv_1311_librivox",
        audio_url=f"{_ARCHIVE}/download/gettysburgaddress_150anniv_1311_librivox/gettysburgaddress_lincoln_amb.mp3",
        excerpt_start=0.0,
        excerpt_end=119.0,
        rights=_rights(
            "gettysburgaddress_150anniv_1311_librivox", License.PUBLIC_DOMAIN_MARK, _PDM
        ),
    ),
    SourceRecord(
        id="declaration-of-independence-michael-scherer",
        title="Declaration of Independence",
        speaker_name="Michael Scherer",
        speaker_sex=Sex.UNSPECIFIED,
        page_url=f"{_ARCHIVE}/details/united_states_documents",
        audio_url=f"{_ARCHIVE}/download/united_states_documents/Declaration_64kb.mp3",
        excerpt_start=0.0,
        excerpt_end=100.0,
        rights=_rights("united_states_documents", License.PUBLIC_DOMAIN_MARK, _PD),
    ),
    SourceRecord(
        id="coming-of-the-end-ian-king",
        title="The Coming of the End",
        speaker_name="Ian King",
        speaker_sex=Sex.UNSPECIFIED,
        page_url=f"{_ARCHIVE}/details/spc153_1603_librivox",
        audio_url=f"{_ARCHIVE}/download/spc153_1603_librivox/spc153_comingoftheend_ik.mp3",
        excerpt_start=0.0,
        excerpt_end=103.3,
        rights=_rights("spc153_1603_librivox", License.PUBLIC_DOMAIN_MARK, _PDM),
    ),
    SourceRecord(
        id="dover-beach-wt",
        title="Dover Beach",
        speaker_name="WT",
        speaker_sex=Sex.UNSPECIFIED,
        page_url=f"{_ARCHIVE}/details/spc164_1702_librivox",
        audio_url=f"{_ARCHIVE}/download/spc164_1702_librivox/spc164_doverbeach_wt.mp3",
        excerpt_start=0.0,
        excerpt_end=90.0,
        rights=_rights("spc164_1702_librivox", License.PUBLIC_DOMAIN_MARK, _PDM),
    ),
    SourceRecord(
        id="new-colossus-as",
        title="The New Colossus",
        speaker_name="AS",
        speaker_sex=Sex.UNSPECIFIED,
        page_url=f"{_ARCHIVE}/details/newcolossus_1207_librivox",
        audio_url=f"{_ARCHIVE}/download/newcolossus_1207_librivox/newcolossus_lazarus_as.mp3",
        excerpt_start=0.0,
        excerpt_end=67.65,
        rights=_rights("newcolossus_1207_librivox", License.PUBLIC_DOMAIN_MARK, _PDM),
    ),
    SourceRecord(
        id="new-colossus-bab",
        title="The New Colossus",
        speaker_name="BAB",
        speaker_sex=Sex.UNSPECIFIED,
        page_url=f"{_ARCHIVE}/details/newcolossus_1207_librivox",
        audio_url=f"{_ARCHIVE}/download/newcolossus_1207_librivox/newcolossus_lazarus_bab.mp3",
        excerpt_start=0.0,
        excerpt_end=88.73,
        rights=_rights("newcolossus_1207_librivox", License.PUBLIC_DOMAIN_MARK, _PDM),
    ),
    SourceRecord(
        id="ozymandias-apc",
        title="Ozymandias",
        speaker_name="APC",
        speaker_sex=Sex.UNSPECIFIED,
        page_url=f"{_ARCHIVE}/details/ozymandias_librivox",
        audio_url=f"{_ARCHIVE}/download/ozymandias_librivox/ozymandias_of_egypt_shelley_apc.mp3",
        excerpt_start=0.0,
        excerpt_end=78.02,
        rights=_rights("ozymandias_librivox", License.PUBLIC_DOMAIN_MARK, _PD),
    ),
    SourceRecord(
        id="ozymandias-db",
        title="Ozymandias",
        speaker_name="DB",
        speaker_sex=Sex.UNSPECIFIED,
        page_url=f"{_ARCHIVE}/details/ozymandias_librivox",
        audio_url=f"{_ARCHIVE}/download/ozymandias_librivox/ozymandias_of_egypt_shelley_db.mp3",
        excerpt_start=0.0,
        excerpt_end=102.51,
        rights=_rights("ozymandias_librivox", License.PUBLIC_DOMAIN_MARK, _PD),
    ),
    SourceRecord(
        id="gettysburg-address-dj",
        title="The Gettysburg Address",
        speaker_name="DJ",
        speaker_sex=Sex.UNSPECIFIED,
        page_url=f"{_ARCHIVE}/details/gettysburgaddress_150anniv_1311_librivox",
        audio_url=f"{_ARCHIVE}/download/gettysburgaddress_150anniv_1311_librivox/gettysburgaddress_lincoln_dj.mp3",
        excerpt_start=0.0,
        excerpt_end=115.0,
        rights=_rights(
            "gettysburgaddress_150anniv_1311_librivox", License.PUBLIC_DOMAIN_MARK, _PDM
        ),
    ),
    SourceRecord(
        id="gettysburg-address-law",
        title="The Gettysburg Address",
        speaker_name="LAW",
        speaker_sex=Sex.UNSPECIFIED,
        page_url=f"{_ARCHIVE}/details/gettysburgaddress_150anniv_1311_librivox",
        audio_url=f"{_ARCHIVE}/download/gettysburgaddress_150anniv_1311_librivox/gettysburgaddress_lincoln_law.mp3",
        excerpt_start=0.0,
        excerpt_end=116.0,
        rights=_rights(
            "gettysburgaddress_150anniv_1311_librivox", License.PUBLIC_DOMAIN_MARK, _PDM
        ),
    ),
)

TEXTS: tuple[TextRecord, ...] = (
    # Public-domain texts are intentionally stored verbatim for offline reproducibility.
    TextRecord(
        id="new-colossus",
        title="The New Colossus",
        category=Category.INTERPRETIVE_READING,
        transcript="Not like the brazen giant of Greek fame, With conquering limbs astride from land to land; Here at our sea-washed, sunset gates shall stand A mighty woman with a torch, whose flame Is the imprisoned lightning, and her name Mother of Exiles. From her beacon-hand Glows world-wide welcome; her mild eyes command The air-bridged harbor that twin cities frame. Keep, ancient lands, your storied pomp! cries she With silent lips. Give me your tired, your poor, Your huddled masses yearning to breathe free, The wretched refuse of your teeming shore. Send these, the homeless, tempest-tost to me, I lift my lamp beside the golden door!",  # noqa: E501
        transcript_url="https://en.wikisource.org/wiki/The_New_Colossus",
    ),
    TextRecord(
        id="ozymandias",
        title="Ozymandias",
        category=Category.INTERPRETIVE_READING,
        transcript="I met a traveller from an antique land, Who said: Two vast and trunkless legs of stone Stand in the desert. Near them, on the sand, Half sunk a shattered visage lies, whose frown, And wrinkled lip, and sneer of cold command, Tell that its sculptor well those passions read Which yet survive, stamped on these lifeless things, The hand that mocked them, and the heart that fed; And on the pedestal, these words appear: My name is Ozymandias, King of Kings; Look on my Works, ye Mighty, and despair! Nothing beside remains. Round the decay Of that colossal Wreck, boundless and bare The lone and level sands stretch far away.",  # noqa: E501
        transcript_url="https://en.wikisource.org/wiki/Ozymandias",
    ),
    TextRecord(
        id="gettysburg-address",
        title="The Gettysburg Address",
        category=Category.DECLAMATION,
        transcript="Four score and seven years ago our fathers brought forth on this continent, a new nation, conceived in Liberty, and dedicated to the proposition that all men are created equal. Now we are engaged in a great civil war, testing whether that nation, or any nation so conceived and so dedicated, can long endure. We are met on a great battle-field of that war. We have come to dedicate a portion of that field, as a final resting place for those who here gave their lives that that nation might live. It is altogether fitting and proper that we should do this. But, in a larger sense, we can not dedicate, we can not consecrate, we can not hallow this ground. The brave men, living and dead, who struggled here, have consecrated it, far above our poor power to add or detract. The world will little note, nor long remember what we say here, but it can never forget what they did here. It is for us the living, rather, to be dedicated here to the unfinished work which they who fought here have thus far so nobly advanced. It is rather for us to be here dedicated to the great task remaining before us that from these honored dead we take increased devotion to that cause for which they gave the last full measure of devotion that we here highly resolve that these dead shall not have died in vain that this nation, under God, shall have a new birth of freedom and that government of the people, by the people, for the people, shall not perish from the earth.",  # noqa: E501
        transcript_url="https://www.gutenberg.org/files/1065/1065-h/1065-h.htm",
    ),
    TextRecord(
        id="declaration-of-independence",
        title="Declaration of Independence",
        category=Category.PERSUASIVE_ORATORY,
        transcript="When in the Course of human events, it becomes necessary for one people to dissolve the political bands which have connected them with another, and to assume among the powers of the earth, the separate and equal station to which the Laws of Nature and of Nature's God entitle them, a decent respect to the opinions of mankind requires that they should declare the causes which impel them to the separation. We hold these truths to be self-evident, that all men are created equal, that they are endowed by their Creator with certain unalienable Rights, that among these are Life, Liberty and the pursuit of Happiness.",  # noqa: E501
        transcript_url="https://www.archives.gov/founding-docs/declaration-transcript",
    ),
    TextRecord(
        id="coming-of-the-end",
        title="The Coming of the End",
        category=Category.INTERPRETIVE_READING,
        transcript="How it came to an end! The meeting afar from the crowd, And the love-looks and laughters unpenned, The parting when much was avowed, How it came to an end! It came to an end; Yes, the outgazing over the stream, With the sun on each serpentine bend, Or, later, the luring moon-gleam; It came to an end. It came to an end, The housebuilding, furnishing, planting, As if there were ages to spend In welcoming, feasting, and jaunting; It came to an end. It came to an end, That journey of one day a week: (It always goes on, said a friend, Just the same in bright weathers or bleak;) But it came to an end. How will come to an end This orbit so smoothly begun, Unless some convulsion attend? I often said. What will be done When it comes to an end? Well, it came to an end Quite silently stopped without jerk; Better close no prevision could lend; Working out as One planned it should work Ere it came to an end.",  # noqa: E501
        transcript_url="https://www.gutenberg.org/cache/epub/3255/pg3255.txt",
    ),
    TextRecord(
        id="dover-beach",
        title="Dover Beach",
        category=Category.INTERPRETIVE_READING,
        transcript="The sea is calm to-night. The tide is full, the moon lies fair Upon the straits; on the French coast the light Gleams and is gone; the cliffs of England stand, Glimmering and vast, out in the tranquil bay. Come to the window, sweet is the night-air! Only, from the long line of spray Where the sea meets the moon-blanched land, Listen! you hear the grating roar Of pebbles which the waves draw back, and fling, At their return, up the high strand, Begin, and cease, and then again begin, With tremulous cadence slow, and bring The eternal note of sadness in.",  # noqa: E501
        transcript_url="https://en.wikisource.org/wiki/Dover_Beach",
    ),
)


def load_texts(work_dir: Path) -> tuple[TextRecord, ...]:
    """Return registry texts with cached cleaned transcripts when present."""
    transcript_dir = work_dir / "transcripts"
    return tuple(
        text.model_copy(
            update={"transcript": (transcript_dir / f"{text.id}.txt").read_text().strip()}
        )
        if (transcript_dir / f"{text.id}.txt").is_file()
        else text
        for text in TEXTS
    )
