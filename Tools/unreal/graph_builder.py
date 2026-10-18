"""Small authoring helpers for UE 5.8's public Blueprint graph APIs.

These scripts run in the editor, never in the shipped game. Gameplay is saved
as ordinary Blueprint assets; no Python or additional runtime plugin is needed.
"""
import unreal as u
import textwrap

LIB = u.BlueprintEditorLibrary
EDITOR = u.BlueprintGraphEditor
ENGINE = '/Script/Engine.'


def class_path(bp):
    return bp.get_path_name() + '_C'


def generated_class(bp):
    return u.load_class(None, class_path(bp))


def pin_type(kind):
    if isinstance(kind, str):
        if kind in ('bool', 'int', 'real', 'name', 'string', 'text'):
            return LIB.get_basic_type_by_name(kind)
        if kind.startswith('array:'):
            return LIB.get_array_type(pin_type(kind[6:]))
        if kind.startswith('/Script/CoreUObject.'):
            return LIB.get_struct_type(u.load_object(None, kind))
        return LIB.get_object_reference_type(u.load_class(None, kind))
    return LIB.get_object_reference_type(kind)


def compile_bp(bp):
    if not LIB.compile_blueprint(bp):
        errors = []
        for graph in LIB.list_graphs(bp):
            editor = EDITOR.get_graph_editor(graph)
            for node in editor.list_nodes_with_errors():
                errors.append(f'{graph.get_name()}: {node.get_node_title()}')
        raise RuntimeError(f'Blueprint compile failed: {bp.get_path_name()} {errors}')


def create_bp(path, parent):
    if u.get_editor_subsystem(u.EditorAssetSubsystem).does_asset_exist(path):
        return u.load_asset(path)
    if isinstance(parent, str):
        parent = u.load_class(None, parent)
    bp = LIB.create_blueprint_asset_with_parent(path, parent)
    if not bp:
        raise RuntimeError('Could not create ' + path)
    compile_bp(bp)
    return bp


def member(bp, name, kind, default=None):
    names = set(LIB.list_member_variable_names(bp, False))
    if name not in names:
        if not LIB.add_member_variable(bp, name, pin_type(kind)):
            raise RuntimeError(f'Could not declare {bp.get_name()}.{name}')
    if default is not None:
        compile_bp(bp)
        u.get_default_object(generated_class(bp)).set_editor_property(name, default)


def declare(bp, name, inputs=None, outputs=None, pure=False):
    old = LIB.find_graph(bp, name)
    if old:
        editor = EDITOR.get_graph_editor(old)
        editor.remove_nodes([n for n in editor.list_all_nodes() if n.get_class().get_name() not in ('K2Node_FunctionEntry', 'K2Node_FunctionResult')])
    else:
        editor = EDITOR.create_and_edit_function_graph(bp, name)
    entry = next(n for n in editor.list_all_nodes() if n.get_class().get_name() == 'K2Node_FunctionEntry')
    existing_inputs = {str(p.get_pin_name()) for p in entry.list_output_pins()}
    for field, kind in (inputs or {}).items():
        if field not in existing_inputs:
            editor.add_graph_input_parameter(field, pin_type(kind), '')
    returns = [n for n in editor.list_all_nodes() if n.get_class().get_name() == 'K2Node_FunctionResult']
    existing_outputs = {str(p.get_pin_name()) for n in returns for p in n.list_input_pins()}
    for field, kind in (outputs or {}).items():
        if field not in existing_outputs:
            editor.add_graph_output_parameter(field, pin_type(kind))
    editor.set_is_pure_function(pure)
    editor.set_function_is_public()
    return editor


def pin(node, name, output=False):
    result = node.find_output_pin(name) if output else node.find_input_pin(name)
    if not result.is_valid():
        available = [str(p.get_pin_name()) for p in node.list_all_pins()]
        raise RuntimeError(f'Missing pin {node.get_name()}.{name}; available={available}')
    return result


def put(target, value):
    if isinstance(value, u.BlueprintGraphPin):
        if not value.try_create_connection(target):
            raise RuntimeError(f'Cannot connect {value.get_pin_name()} -> {target.get_pin_name()}')
    else:
        if isinstance(value, bool):
            value = 'true' if value else 'false'
        elif isinstance(value, u.Object):
            value = value.get_path_name()
        elif value is None:
            value = 'None'
        if not target.set_pin_value(str(value)):
            raise RuntimeError(f'Cannot set {target.get_pin_name()}={value}')


class Graph:
    """Fail-fast graph construction with explicit execution and data connections."""

    def __init__(self, bp, name, tail=None):
        self.bp = bp
        self.editor = EDITOR.get_graph_editor_by_name(bp, name)
        if not self.editor:
            raise RuntimeError(f'Missing graph {bp.get_name()}.{name}')
        self.name = name
        self.tail = tail
        if tail is None and name != 'EventGraph':
            self.tail = self.editor.find_graph_entry_pin()
        self.created = []

    def at(self, tail):
        return Graph(self.bp, self.name, tail)

    def own(self, node):
        if not node:
            raise RuntimeError(f'Could not create node in {self.bp.get_name()}.{self.name}')
        self.created.append(node)
        return node

    def wire_exec(self, node):
        candidates = [p for p in node.list_input_pins() if str(p.get_pin_type_display_string()) == 'Exec']
        if candidates:
            inp = candidates[0]
            tails = self.tail if isinstance(self.tail, list) else [self.tail]
            if not tails or any(p is None or not p.is_valid() for p in tails):
                raise RuntimeError(f'No execution source for {node.get_name()}')
            for source in tails:
                put(inp, source)
            outputs = [p for p in node.list_output_pins() if str(p.get_pin_type_display_string()) == 'Exec']
            self.tail = next((p for p in outputs if str(p.get_pin_name()) == 'then'), outputs[0] if outputs else None)
        return node

    def call(self, function, result=None, /, **args):
        node = self.own(self.editor.add_call_function_node(function))
        # Connections resolve wildcard types before literal defaults are assigned.
        ordered = sorted(args.items(), key=lambda kv: not isinstance(kv[1], u.BlueprintGraphPin))
        for name, value in ordered:
            put(pin(node, name), value)
        self.wire_exec(node)
        return pin(node, result, True) if result else node

    def engine(self, owner, method, result=None, /, **args):
        return self.call(ENGINE + owner + '.' + method, result, **args)

    def math(self, method, **args):
        # Math function spawners may emit promotable operators. Typed literals
        # make their specialization deterministic (rather than wildcard defaults).
        values = {k: self.literal(v) if isinstance(v, (bool, int, float)) else v for k, v in args.items()}
        return self.engine('KismetMathLibrary', method, 'ReturnValue', **values)

    def literal(self, value):
        if isinstance(value, u.BlueprintGraphPin):
            return value
        kind = 'Bool' if isinstance(value, bool) else 'Int' if isinstance(value, int) else 'Double' if isinstance(value, float) else 'String'
        return self.engine('KismetSystemLibrary', 'MakeLiteral' + kind, 'ReturnValue', Value=value)

    def get(self, name, obj=None, cls=''):
        node = self.own(self.editor.add_get_member_variable_node(name, cls))
        if obj is not None:
            put(pin(node, 'self'), obj)
        return pin(node, name, True)

    def set(self, name, value, obj=None, cls=''):
        if name in ('StatusText', 'FailureText') and isinstance(value, str):
            value = textwrap.fill(value, width=68)
        node = self.own(self.editor.add_set_member_variable_node(name, cls))
        if obj is not None:
            put(pin(node, 'self'), obj)
        put(pin(node, name), value)
        return self.wire_exec(node)

    def param(self, name):
        entry = next(n for n in self.editor.list_all_nodes() if n.get_class().get_name() == 'K2Node_FunctionEntry')
        return pin(entry, name, True)

    def branch(self, condition):
        node = self.own(self.editor.add_branch_node())
        put(pin(node, 'Condition'), condition)
        self.wire_exec(node)
        return self.at(node.find_then_pin()), self.at(node.find_else_pin())

    def guard(self, condition, otherwise=None):
        yes, no = self.branch(condition)
        if otherwise:
            otherwise(no)
        self.tail = yes.tail
        return self

    def when(self, condition, action):
        yes, no = self.branch(condition)
        action(yes)
        tails = yes.tail if isinstance(yes.tail, list) else [yes.tail]
        self.tail = [p for p in tails if p is not None] + [no.tail]
        return self

    def ret(self, **values):
        node = self.own(self.editor.add_return_node())
        for name, value in values.items():
            put(pin(node, name), value)
        self.wire_exec(node)
        self.tail = None

    def event(self, name, override=True):
        node = LIB.add_event_override(self.bp, name, u.IntPoint(0, len(self.editor.list_all_nodes()) * 200)) if override else self.editor.add_custom_event_node(name)
        self.own(node)
        self.tail = node.find_then_pin()
        return node

    def cast(self, obj, cls):
        target = u.load_class(None, cls) if isinstance(cls, str) else cls
        if target.get_path_name() in str(obj.get_pin_type_as_json_schema()):
            return obj
        name = target.get_name()
        if name.endswith('_C'):
            name = name[:-2]
        wanted = ('CastTo' + name).replace('_', '').lower()
        actions = self.editor.list_available_nodes([obj])
        matches = [str(a) for a in actions if str(a).rsplit('|', 1)[-1].replace('_', '').lower() == wanted]
        if matches:
            node = self.own(self.editor.create_node_from_name(matches[0], u.Vector2D(0, 0), [obj], None))
        else:
            # Newly authored classes do not enter the deferred action database
            # until an editor tick. Retarget an ordinary native cast using the
            # supported API rather than depending on asset-menu refresh timing.
            node = self.own(self.editor.create_node_from_name('Utilities|Casting|CastToActor', u.Vector2D(0, 0), [], None))
            if not self.editor.retarget_node_class(node, u.Actor.static_class(), target):
                raise RuntimeError('Could not retarget cast to ' + name)
        put(pin(node, 'Object'), obj)
        self.wire_exec(node)
        outputs = [p for p in node.list_output_pins() if str(p.get_pin_name()).startswith('As')]
        if len(outputs) != 1:
            raise RuntimeError('Invalid cast outputs: ' + name)
        return outputs[0]

    def spawn(self, cls, transform):
        node = self.own(self.editor.create_node_from_name('Game|SpawnActorfromClass', u.Vector2D(0, 0), [], None))
        put(pin(node, 'Class'), cls)
        put(pin(node, 'SpawnTransform'), transform)
        put(pin(node, 'CollisionHandlingOverride'), 'AdjustIfPossibleButDontSpawnIfColliding')
        self.wire_exec(node)
        return pin(node, 'ReturnValue', True)

    def foreach(self, array):
        macro = u.load_asset('/Engine/EditorBlueprintResources/StandardMacros')
        graph = LIB.find_graph(macro, 'ForEachLoop')
        node = self.own(self.editor.add_macro_node(graph.get_path_name()))
        put(pin(node, 'Array'), array)
        self.wire_exec(node)
        self.tail = pin(node, 'Completed', True)
        return self.at(pin(node, 'LoopBody', True)), pin(node, 'Array Element', True)

    def valid(self, obj):
        return self.engine('KismetSystemLibrary', 'IsValid', 'ReturnValue', Object=obj)

    def not_(self, b):
        return self.math('Not_PreBool', A=b)

    def and_(self, *items):
        result = items[0]
        for item in items[1:]:
            result = self.math('BooleanAND', A=result, B=item)
        return result

    def or_(self, *items):
        result = items[0]
        for item in items[1:]:
            result = self.math('BooleanOR', A=result, B=item)
        return result

    def eq(self, a, b):
        return self.math('EqualEqual_IntInt', A=a, B=b)

    def vec(self, x, y, z):
        return self.engine('KismetMathLibrary', 'MakeVector', 'ReturnValue', X=x, Y=y, Z=z)

    def rot(self, pitch=0, yaw=0, roll=0):
        return self.engine('KismetMathLibrary', 'MakeRotator', 'ReturnValue', Pitch=pitch, Yaw=yaw, Roll=roll)

    def transform(self, location, rotation=None):
        args = {'Location': location, 'Scale': '1,1,1'}
        if rotation is not None:
            args['Rotation'] = rotation
        return self.engine('KismetMathLibrary', 'MakeTransform', 'ReturnValue', **args)

    def log(self, text):
        return self.engine('KismetSystemLibrary', 'PrintString', InString=text, bPrintToScreen=False, bPrintToLog=True)


def layout(bp):
    for graph in LIB.list_graphs(bp):
        editor = EDITOR.get_graph_editor(graph)
        for i, node in enumerate(editor.list_all_nodes()):
            node.set_node_pos(u.IntPoint((i % 7) * 400, (i // 7) * 260))


def save(bp):
    compile_bp(bp)
    layout(bp)
    if not u.get_editor_subsystem(u.EditorAssetSubsystem).save_loaded_asset(bp, False):
        raise RuntimeError('Could not save ' + bp.get_path_name())
