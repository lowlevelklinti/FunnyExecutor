offsetFields = [
    ("fakeDatamodelPtr", "fake_datamodel_ptr"),
    ("realDatamodelPtr", "real_datamodel_ptr"),
    ("insName", "ins_name"),
    ("insNameContainer", "ins_name_container"),
    ("insClassDesc", "ins_class_desc"),
    ("insClassName", "ins_class_name"),
    ("insParent", "ins_parent"),
    ("insChildrenStart", "ins_children_start"),
    ("insChildrenEnd", "ins_children_end"),
    ("moduleBytecode", "module_bytecode"),
    ("bytecodePtr", "bytecode_ptr"),
    ("bytecodeSize", "bytecode_size"),
    ("fflagEnableLoadModule", "fflag_enable_load_module"),
    ("value", "value"),
    ("stringLength", "string_length"),
]

generatedSource = """class Offsets:
    def __init__(self, data):"""
for attributeName, dataKey in offsetFields:
    generatedSource += f'\n        self.{attributeName} = data["{dataKey}"]'

generatedSource += '\n        self.fflagTaskSchedulerTargetFps = data.get("fflag_task_scheduler_target_fps")'

print(generatedSource)
