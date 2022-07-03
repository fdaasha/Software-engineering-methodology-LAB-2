import os, javalang, sys
from enum import Enum

class MemberType(Enum):
    FIELDS = 'fields'
    METHODS = 'methods'

class ModifierType(Enum):
    PRIVATE = 'private'
    PUBLIC = 'public'

class GlobalContext:
    def __init__(self):
        self.inheretence_dict = {}
        self.mood_metrix = None

class MoodMetrictsData:
    def __init__(self):
        self.mif = 0
        self.mhf = 0
        self.ahf = 0
        self.aif = 0
        self.pof = 0

class ClassData:
    def __init__(self, name, methods, fields, package='', parent=None):
        self.name = name
        self.package = package
        self.methods = methods
        self.fields = fields
        self.parent = parent
        self.direct_children = []
        self.all_children = []
        self.mood_metrics = None
        self.inheritance_depth = 0
        self.inherited_members = {MemberType.FIELDS:[], MemberType.METHODS:[]}
    
    def get_full_name(self):
        if self.package != '':
            return self.package + '.' + self.name
        return self.name

def upload_file_data(ctxt, file_path):
    with open(file_path, encoding="utf-8") as f:
        tree = javalang.parse.parse(f.read())
        package = tree.package.name if tree.package is not None else ''
        imports = [imprt.path for imprt in tree.imports]
        types = [type.name for type in tree.types]
        for type in tree.types:
            if isinstance(type, javalang.parser.tree.ClassDeclaration):
                parent_type = None
                if type.extends is not None:
                    parent_type = type.extends.name
                    if parent_type not in types:
                        for imprt in imports:
                            if f".{parent_type}" in imprt:
                                parent_type = imprt
                                break
                methods = type.methods
                fields = type.fields
                class_data = ClassData(type.name, methods, fields, package, parent_type)
                ctxt.inheretence_dict[class_data.get_full_name()] = class_data;
            
def add_inherited_members(class_data):
    fmethod = list(filter(lambda m: not any([annotation.name == 'Override' for annotation in m.annotations]), class_data.methods))
    methods = fmethod + class_data.inherited_members[MemberType.METHODS]
    ffield = list(filter(lambda m: not any([annotation.name == 'Override' for annotation in m.annotations]), class_data.fields))
    fields = ffield + class_data.inherited_members[MemberType.FIELDS]
    for child_name in class_data.direct_children:
        if child_name in ctxt.inheretence_dict:
            child_data = ctxt.inheretence_dict[child_name]
            child_data.inherited_members[MemberType.METHODS] += methods
            child_data.inherited_members[MemberType.FIELDS] += fields
            add_inherited_members(child_data)
            
def completed_parent_name(ctxt, parent_name):
    return '.' in parent_name or parent_name in ctxt.inheretence_dict

def calculate_inheritance(ctxt):
    for class_data in ctxt.inheretence_dict.values():
        if class_data.parent is not None and not completed_parent_name(ctxt, class_data.parent):
            full_parent_name = class_data.package + '.' + class_data.parent
            if ctxt.inheretence_dict.get(full_parent_name, None) is not None:
                class_data.parent = full_parent_name
            
    for class_data in ctxt.inheretence_dict.values():
        if class_data.parent is not None and class_data.parent in ctxt.inheretence_dict:
            ctxt.inheretence_dict[class_data.parent].direct_children.append(class_data.get_full_name())
            curr_data = class_data
            child_name = class_data.get_full_name()
            inheritance_depth = 0
            while curr_data.parent is not None and completed_parent_name(ctxt, curr_data.parent):
                curr_data = ctxt.inheretence_dict[curr_data.parent]
                if child_name not in curr_data.all_children:
                    curr_data.all_children.append(child_name)
                inheritance_depth += 1
            class_data.inheritance_depth = inheritance_depth
        
    for class_data in ctxt.inheretence_dict.values():
        if class_data.parent is None:
            add_inherited_members(class_data)

def get_members_by_type_and_modifier(class_data, type: MemberType, modifier: ModifierType):
    members = class_data.methods if type == MemberType.METHODS else class_data.fields
    check_func = (lambda member: ModifierType.PRIVATE.value in member.modifiers) if modifier == ModifierType.PRIVATE \
        else (lambda member: ModifierType.PRIVATE.value not in member.modifiers)
    return list(filter(check_func, members))


def compare_methods(method1, method2) -> bool:
    if method1.name != method2.name:
        return False
    if len(method1.parameters) != len(method2.parameters):
        return False
    method1_params = [{'name': p.name, 'type': p.type.name} for p in method1.parameters]
    method2_params = [{'name': p.name, 'type': p.type.name} for p in method2.parameters]
    if method1_params != method2_params:
        return False
    return True

def compare_fields(filed1, field2) -> bool:
    if filed1.declarators[0].name != field2.declarators[0].name:
        return False
    if filed1.type != field2.type:
        return False
    return True

def get_inherited_members_by_params(class_data, type: MemberType, overrided):
    own_members = class_data.methods if type == MemberType.METHODS else class_data.fields
    compare = compare_methods if type == MemberType.METHODS else compare_fields
    filter_func = (lambda im: any(compare(im, member) for member in own_members)) if overrided \
        else (lambda im: not any(compare(im, member) for member in own_members))
    return list(filter(filter_func, class_data.inherited_members[type]))
    
def calculate_mood_metrics(ctxt):
    public_methods_len = 0
    private_methods_len = 0
    public_fields_len = 0
    private_fields_len = 0
    inherited_not_overrided_methods_len = 0
    locally_defined_and_inherited_methods_len  = 0
    inherited_not_overrided_fields_len = 0
    locally_defined_and_inherited_fields_len = 0
    pof_denominator = 0
    inherited_overrided_methods_len = 0
    for class_data in ctxt.inheretence_dict.values():
        class_public_methods_len = len(get_members_by_type_and_modifier(class_data, MemberType.METHODS, ModifierType.PUBLIC))
        public_methods_len += class_public_methods_len
        class_private_methods_len = len(get_members_by_type_and_modifier(class_data, MemberType.METHODS, ModifierType.PRIVATE))
        private_methods_len += class_private_methods_len
        class_public_fields_len = len(get_members_by_type_and_modifier(class_data, MemberType.FIELDS, ModifierType.PUBLIC))
        public_fields_len += class_public_fields_len
        class_private_fields_len = len(get_members_by_type_and_modifier(class_data, MemberType.FIELDS, ModifierType.PRIVATE))
        private_fields_len += class_private_fields_len
        inherited_not_overrided_methods_len += len(get_inherited_members_by_params(class_data, MemberType.METHODS, False))
        inherited_not_overrided_fields_len += len(get_inherited_members_by_params(class_data, MemberType.FIELDS, False))
        locally_defined_and_inherited_methods_len += class_public_methods_len + class_private_methods_len + len(class_data.inherited_members[MemberType.METHODS])
        locally_defined_and_inherited_fields_len += class_public_fields_len + class_private_fields_len + len(class_data.inherited_members[MemberType.FIELDS])
        pof_denominator += len(class_data.all_children) * len(class_data.methods)
        inherited_overrided_methods_len += len(get_inherited_members_by_params(class_data, MemberType.METHODS, True))
    if pof_denominator == 0:
        raise Exception("pof_denominator is 0")
    ctxt.mood_metrix = {
        'mhf': private_methods_len / (public_methods_len + private_methods_len),
        'ahf': private_fields_len / (public_fields_len  + private_fields_len),
        'mif': inherited_not_overrided_methods_len / locally_defined_and_inherited_methods_len,
        'aif': inherited_not_overrided_fields_len / locally_defined_and_inherited_fields_len,
        'pof': inherited_overrided_methods_len / pof_denominator
    }
    
    
def print_mood_metrix(ctxt):
    print("MOOD metrix:")
    for key, value in ctxt.mood_metrix.items():
        print(f"{key}: {value}")
        
def print_class_metrix(ctxt):
    print("Class metrix:")
    inheritance_depth = 0
    for name, value in ctxt.inheretence_dict.items():
        print(f"{name} has {len(value.all_children)} children")
        if value.inheritance_depth > inheritance_depth:
            inheritance_depth = value.inheritance_depth
    print(f"Depth of Inheritance Tree: {inheritance_depth}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        exit(1)

    ctxt = GlobalContext()
    # lib_path = "E:\\projects\\mipz_practice2\\test"
    lib_path = sys.argv[1]
    for root, _, files in os.walk(lib_path):
        for file in files:
            if file.endswith('.java'):
                try:
                    upload_file_data(ctxt, os.path.join(root, file))
                except Exception as e:
                    print(str(e))
    calculate_inheritance(ctxt)
    calculate_mood_metrics(ctxt)
    print_mood_metrix(ctxt)
    print_class_metrix(ctxt)
    
    