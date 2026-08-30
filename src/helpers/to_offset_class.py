offsets = [
    "fake_datamodel_ptr",
    "real_datamodel_ptr",
    "ins_name",
    "ins_name_container",
    "ins_class_desc",
    "ins_class_name",
    "ins_parent",
    "ins_children_start",
    "ins_children_end",
    "module_bytecode",
    "bytecode_ptr",
    "bytecode_size",
    "fflag_enable_load_module",
    "value",
    "string_length"
]

thing = """class Offsets:
    def __init__(self, data):"""
for i in offsets:
    thing+=f'\n        self.{i} = data["{i}"]'

print(thing)