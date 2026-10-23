from copy import deepcopy
from pathlib import Path
import re
import xml.etree.ElementTree as ET


SOURCE_PATH = Path(
    r"C:\Users\lilly\AppData\LocalLow\Ludeon Studios\RimWorld by Ludeon Studios"
    r"\PawnEditor\StartingPreset\Colony 1.xml"
)
OUTPUT_PATH = Path(
    r"C:\Users\lilly\AppData\LocalLow\Ludeon Studios\RimWorld by Ludeon Studios"
    r"\PawnEditor\StartingPreset\Colony 32.xml"
)
TARGET_COUNT = 32


def main():
    tree = ET.parse(SOURCE_PATH)
    root = tree.getroot()
    humans = root.find("humans")
    if humans is None:
        raise ValueError("The source XML does not contain StartingPreset.humans.")

    entries = humans.findall("li")
    if not entries:
        raise ValueError("StartingPreset.humans does not contain a human li entry.")
    if len(entries) > TARGET_COUNT:
        raise ValueError(
            f"The source already contains {len(entries)} humans; "
            f"cannot expand it to exactly {TARGET_COUNT} without removing entries."
        )

    template = entries[0]
    id_node = template.find("id")
    if id_node is None or not id_node.text:
        raise ValueError("The first human entry does not have an ID.")
    starting_possessions = root.find("startingPossessions")
    if starting_possessions is None:
        raise ValueError("The source XML does not contain StartingPreset.startingPossessions.")
    possession_keys = starting_possessions.find("keys")
    possession_values = starting_possessions.find("values")
    if possession_keys is None or possession_values is None:
        raise ValueError("StartingPreset.startingPossessions must contain keys and values.")
    keys = possession_keys.findall("li")
    values = possession_values.findall("li")
    if len(keys) != len(entries) or len(values) != len(entries):
        raise ValueError(
            "The startingPossessions keys and values must match the human count."
        )

    template_key = keys[0]
    template_value = values[0]
    if [node.text for node in template.iter("id")] != [
        node.text for node in template_key.iter("id")
    ]:
        raise ValueError(
            "The first startingPossessions key does not mirror the first human entry."
        )

    used_ids = {
        node.text for node in root.iter("id") if node.text is not None
    }
    template_ids = [node.text for node in template.iter("id") if node.text]
    if len(template_ids) != len(set(template_ids)):
        raise ValueError("The first human entry contains duplicate IDs.")

    numeric_id_suffixes = [
        int(match.group(1))
        for value in used_ids
        if (match := re.search(r"(\d+)$", value)) is not None
    ]
    next_id_number = max(numeric_id_suffixes, default=0) + 1

    used_load_ids = {
        node.text for node in root.iter("loadID") if node.text is not None
    }
    numeric_load_ids = [
        int(value) for value in used_load_ids if value.isdecimal()
    ]
    next_load_id = max(numeric_load_ids, default=0) + 1

    while len(entries) < TARGET_COUNT:
        clone = deepcopy(template)
        clone_key = deepcopy(template_key)
        clone_value = deepcopy(template_value)
        cloned_ids = [node.text for node in clone.iter("id") if node.text]
        key_ids = [node.text for node in clone_key.iter("id") if node.text]
        if cloned_ids != key_ids:
            raise ValueError("The cloned startingPossessions key does not mirror its human.")

        id_mapping = {}
        for old_id in cloned_ids:
            match = re.fullmatch(r"(.*?)(\d+)", old_id)
            id_prefix = match.group(1) if match else f"{old_id}_"
            while True:
                new_id = f"{id_prefix}{next_id_number}"
                next_id_number += 1
                if new_id not in used_ids:
                    break

            id_mapping[old_id] = new_id
            used_ids.add(new_id)

        id_pattern = re.compile(
            "|".join(re.escape(value) for value in sorted(id_mapping, key=len, reverse=True))
        )
        for record in (clone, clone_key):
            for node in record.iter():
                if node.text and id_pattern.pattern:
                    node.text = id_pattern.sub(
                        lambda match: id_mapping[match.group(0)], node.text
                    )

        cloned_numeric_load_ids = {
            node.text
            for record in (clone, clone_key)
            for node in record.iter("loadID")
            if node.text and node.text.isdecimal()
        }
        load_id_mapping = {}
        for old_load_id in sorted(cloned_numeric_load_ids, key=int):
            while str(next_load_id) in used_load_ids:
                next_load_id += 1
            load_id_mapping[old_load_id] = str(next_load_id)
            used_load_ids.add(str(next_load_id))
            next_load_id += 1

        for record in (clone, clone_key):
            for load_id in record.iter("loadID"):
                if load_id.text in load_id_mapping:
                    load_id.text = load_id_mapping[load_id.text]

        humans.append(clone)
        possession_keys.append(clone_key)
        possession_values.append(clone_value)
        entries.append(clone)
        keys.append(clone_key)
        values.append(clone_value)

    for human in entries:
        human_id = human.findtext("id")
        if not human_id:
            raise ValueError("A human entry does not have an ID.")
        for pawn_ref in human.findall("./genes/xenogenes/li/pawn"):
            expected_ref = f"Thing_{human_id}"
            if pawn_ref.text != expected_ref:
                raise ValueError(
                    f"Human {human_id} has an unexpected xenogene pawn reference: "
                    f"{pawn_ref.text!r}"
                )
        for pawn_ref in human.findall("./genes/endogenes/li/pawn"):
            expected_ref = f"Thing_{human_id}"
            if pawn_ref.text != expected_ref:
                raise ValueError(
                    f"Human {human_id} has an unexpected endogene pawn reference: "
                    f"{pawn_ref.text!r}"
                )

    human_ids = [human.findtext("id") for human in entries]
    if len(set(human_ids)) != TARGET_COUNT:
        raise ValueError("Human IDs are not unique after cloning.")
    taking_count = root.find("takingCount")
    if taking_count is None:
        raise ValueError("The source XML does not contain StartingPreset.takingCount.")
    taking_count.text = str(TARGET_COUNT)
    if len(keys) != TARGET_COUNT or len(values) != TARGET_COUNT:
        raise ValueError("The output startingPossessions entries do not match the human count.")

    entity_ids = []
    pawn_load_ids = []
    for human, key in zip(entries, keys):
        human_entity_ids = [node.text for node in human.iter("id") if node.text]
        key_entity_ids = [node.text for node in key.iter("id") if node.text]
        if human_entity_ids != key_entity_ids:
            raise ValueError("A startingPossessions key does not mirror its human entry.")
        entity_ids.extend(human_entity_ids)
        human_load_ids = [node.text for node in human.iter("loadID") if node.text]
        key_load_ids = [node.text for node in key.iter("loadID") if node.text]
        if human_load_ids != key_load_ids:
            raise ValueError("A startingPossessions key has mismatched loadIDs.")
        pawn_load_ids.extend(human_load_ids)

    if len(entity_ids) != len(set(entity_ids)):
        raise ValueError("The output contains duplicate entity IDs across human entries.")
    if len(pawn_load_ids) != len(set(pawn_load_ids)):
        raise ValueError("The output contains duplicate loadIDs across human entries.")

    ET.indent(tree, space="\t")
    tree.write(OUTPUT_PATH, encoding="utf-8", xml_declaration=True)
    print(
        f"Created {OUTPUT_PATH} with {TARGET_COUNT} humans "
        f"and takingCount={taking_count.text}."
    )


if __name__ == "__main__":
    main()
