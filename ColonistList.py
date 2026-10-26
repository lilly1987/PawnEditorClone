from copy import deepcopy
from pathlib import Path
import re
import xml.etree.ElementTree as ET


SOURCE_PATH = Path(
    r"C:\Users\lilly\AppData\LocalLow\Ludeon Studios\RimWorld by Ludeon Studios"
    r"\PawnEditor\ColonistList\Humans\Colonists 1.xml"
)
OUTPUT_PATH = Path(
    r"C:\Users\lilly\AppData\LocalLow\Ludeon Studios\RimWorld by Ludeon Studios"
    r"\PawnEditor\ColonistList\Humans\Colonists 32.xml"
)
TARGET_COUNT = 32


def main():
    tree = ET.parse(SOURCE_PATH)
    root = tree.getroot()
    if root.tag != "ColonistList.Humans":
        raise ValueError(f"Unexpected source XML root: {root.tag}.")

    colonists = root.find("colonists")
    if colonists is None:
        raise ValueError("The source XML does not contain ColonistList.Humans.colonists.")

    entries = colonists.findall("li")
    if not entries:
        raise ValueError("The source colonists list does not contain a human li entry.")
    if len(entries) > TARGET_COUNT:
        raise ValueError(
            f"The source already contains {len(entries)} colonists; "
            f"cannot expand it to exactly {TARGET_COUNT} without removing entries."
        )

    templates = []
    for human in entries:
        human_id = human.findtext("id")
        if not human_id:
            raise ValueError("A source human entry does not have an ID.")
        entity_ids = [
            node.text for node in human.iter("id") if node.text
        ]
        if len(entity_ids) != len(set(entity_ids)):
            raise ValueError(f"Human {human_id} contains duplicate entity IDs.")
        templates.append(human)

    used_ids = {node.text for node in root.iter("id") if node.text}
    if len(used_ids) != sum(1 for node in root.iter("id") if node.text):
        raise ValueError("The source XML contains duplicate entity IDs.")

    used_load_ids = {node.text for node in root.iter("loadID") if node.text}
    if len(used_load_ids) != sum(1 for node in root.iter("loadID") if node.text):
        raise ValueError("The source XML contains duplicate loadIDs.")

    numeric_id_suffixes = [
        int(match.group(1))
        for value in used_ids
        if (match := re.search(r"(\d+)$", value)) is not None
    ]
    next_id_number = max(numeric_id_suffixes, default=0) + 1

    numeric_load_ids = [
        int(value) for value in used_load_ids if value.isdecimal()
    ]
    next_load_id = max(numeric_load_ids, default=0) + 1

    template_index = 0
    while len(entries) < TARGET_COUNT:
        template = templates[template_index % len(templates)]
        template_index += 1
        clone = deepcopy(template)

        cloned_ids = [node.text for node in clone.iter("id") if node.text]
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
            "|".join(
                re.escape(value)
                for value in sorted(id_mapping, key=len, reverse=True)
            )
        )

        def replace_entity_ids(value):
            if not value or not id_mapping:
                return value
            return id_pattern.sub(lambda match: id_mapping[match.group(0)], value)

        for node in clone.iter():
            node.text = replace_entity_ids(node.text)
            for attribute_name, attribute_value in node.attrib.items():
                node.set(attribute_name, replace_entity_ids(attribute_value))

        for load_id in clone.iter("loadID"):
            if load_id.text and load_id.text.isdecimal():
                while str(next_load_id) in used_load_ids:
                    next_load_id += 1
                new_load_id = str(next_load_id)
                next_load_id += 1
                used_load_ids.add(new_load_id)
                load_id.text = new_load_id
            elif load_id.text:
                load_id.text = replace_entity_ids(load_id.text)
                if load_id.text in used_load_ids:
                    raise ValueError(
                        f"Cloning created a duplicate loadID: {load_id.text}."
                    )
                used_load_ids.add(load_id.text)

        colonists.append(clone)
        entries.append(clone)

    for human in entries:
        human_id = human.findtext("id")
        if not human_id:
            raise ValueError("A human entry does not have an ID.")
        for pawn_ref in human.findall("./genes/xenogenes/li/pawn"):
            if pawn_ref.text != f"Thing_{human_id}":
                raise ValueError(
                    f"Human {human_id} has an unexpected xenogene pawn reference: "
                    f"{pawn_ref.text!r}"
                )
        for pawn_ref in human.findall("./genes/endogenes/li/pawn"):
            if pawn_ref.text != f"Thing_{human_id}":
                raise ValueError(
                    f"Human {human_id} has an unexpected endogene pawn reference: "
                    f"{pawn_ref.text!r}"
                )

    human_ids = [human.findtext("id") for human in entries]
    if len(human_ids) != TARGET_COUNT or len(set(human_ids)) != TARGET_COUNT:
        raise ValueError("Human IDs are not unique after cloning.")

    all_ids = [node.text for node in root.iter("id") if node.text]
    if len(all_ids) != len(set(all_ids)):
        raise ValueError("The output contains duplicate entity IDs.")
    all_load_ids = [node.text for node in root.iter("loadID") if node.text]
    if len(all_load_ids) != len(set(all_load_ids)):
        raise ValueError("The output contains duplicate loadIDs.")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(tree, space="\t")
    tree.write(OUTPUT_PATH, encoding="utf-8", xml_declaration=True)
    print(f"Created {OUTPUT_PATH} with {TARGET_COUNT} colonists.")


if __name__ == "__main__":
    main()
