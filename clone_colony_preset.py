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
    used_ids = {
        node.text for node in root.iter("id") if node.text is not None
    }
    template_ids = [
        node.text for node in template.iter("id") if node.text is not None
    ]
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
        id_mapping = {}
        for clone_id in clone.iter("id"):
            old_id = clone_id.text
            if not old_id:
                continue

            match = re.fullmatch(r"(.*?)(\d+)", old_id)
            id_prefix = match.group(1) if match else f"{old_id}_"
            while True:
                new_id = f"{id_prefix}{next_id_number}"
                next_id_number += 1
                if new_id not in used_ids:
                    break

            id_mapping[old_id] = new_id
            used_ids.add(new_id)

        for node in clone.iter():
            if node.text:
                for old_id, new_id in sorted(
                    id_mapping.items(), key=lambda item: len(item[0]), reverse=True
                ):
                    node.text = node.text.replace(old_id, new_id)

        for gene_load_id in clone.findall(
            "./genes/xenogenes/li/loadID"
        ) + clone.findall("./genes/endogenes/li/loadID"):
            while str(next_load_id) in used_load_ids:
                next_load_id += 1
            gene_load_id.text = str(next_load_id)
            used_load_ids.add(str(next_load_id))
            next_load_id += 1

        humans.append(clone)
        entries.append(clone)

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
    all_ids = [
        node.text for node in root.iter("id") if node.text is not None
    ]
    if len(set(all_ids)) != len(all_ids):
        raise ValueError("The output contains duplicate entity IDs.")
    all_load_ids = [
        node.text for node in root.iter("loadID") if node.text is not None
    ]
    if len(set(all_load_ids)) != len(all_load_ids):
        raise ValueError("The output contains duplicate loadIDs.")

    ET.indent(tree, space="\t")
    tree.write(OUTPUT_PATH, encoding="utf-8", xml_declaration=True)
    print(
        f"Created {OUTPUT_PATH} with {TARGET_COUNT} humans "
        f"and takingCount={taking_count.text}."
    )


if __name__ == "__main__":
    main()
